"""EDI gateway tests"""

from collections import namedtuple
from contextlib import contextmanager
from datetime import timedelta
import os
import pathlib
import socket
import shutil
import tempfile
import threading
from unittest.mock import patch
import paramiko
from odoo import fields
from odoo.tools import config
from .common import EdiCase, EdiTestFile


def skipUnlessCanInitiate(f):
    """Skip test case unless gateway is capable of initiating connections"""
    def wrapper(self, *args, **kwargs):
        # pylint: disable=missing-docstring
        if self.gateway.can_initiate:
            f(self, *args, **kwargs)
        else:
            self.skipTest("Gateway cannot initiate connections")
    return wrapper


def skipUnlessCanReceive(f):
    """Skip test case unless gateway is capable of receiving"""
    def wrapper(self, *args, **kwargs):
        # pylint: disable=missing-docstring
        if self.gateway.path_ids.filtered(lambda x: x.allow_receive):
            f(self, *args, **kwargs)
        else:
            self.skipTest("Gateway has no receive paths")
    return wrapper


def skipUnlessCanSend(f):
    """Skip test case unless gateway is capable of sending"""
    def wrapper(self, *args, **kwargs):
        # pylint: disable=missing-docstring
        if self.gateway.path_ids.filtered(lambda x: x.allow_send):
            f(self, *args, **kwargs)
        else:
            self.skipTest("Gateway has no send paths")
    return wrapper


class DummySSHServer(paramiko.ServerInterface):
    """Dummy SSH server"""

    DEFAULT_USERNAME = 'user'
    DEFAULT_PASSWORD = 'pass'

    def __init__(self, host_key, username=DEFAULT_USERNAME,
                 password=DEFAULT_PASSWORD):
        self.host_key = host_key
        self.username = username
        self.password = password

    def connect(self, *args, orig_connect=paramiko.SSHClient.connect, **kwargs):
        """Connect to dummy SSH server"""
        (client_sock, server_sock) = socket.socketpair()
        self.create_transport(server_sock)
        return orig_connect(*args, sock=client_sock, **kwargs)

    def create_transport(self, sock):
        """Create transport for dummy SSH server"""
        transport = paramiko.Transport(sock)
        transport.add_server_key(
            paramiko.RSAKey.from_private_key_file(self.host_key)
        )
        transport.start_server(server=self, event=threading.Event())
        return transport

    def check_auth_password(self, username, password):
        """Check username and password"""
        if username == self.username and password == self.password:
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_channel_request(self, kind, chanid):
        """Allow any channel to be opened"""
        return paramiko.OPEN_SUCCEEDED


class EdiGatewayCase(EdiCase):
    """Abstract base test case for EDI gateways"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        IrModel = cls.env['ir.model']
        EdiGateway = cls.env['edi.gateway']
        EdiPath = cls.env['edi.gateway.path']

        # Create gateway
        cls.gateway = EdiGateway.create({
            'name': "Test gateway",
            'model_id': IrModel._get_id('edi.connection.model'),
        })

        # Create paths
        cls.path_receive = EdiPath.create({
            'name': "Test receive path",
            'gateway_id': cls.gateway.id,
            'path': '/',
            'allow_receive': True,
            'allow_send': False,
        })
        cls.path_send = EdiPath.create({
            'name': "Test send path",
            'gateway_id': cls.gateway.id,
            'path': '/',
            'allow_receive': False,
            'allow_send': True,
            'doc_type_ids': [(6, 0, cls.doc_type_unknown.ids)],
        })

        # Dummy SSH server class
        cls.SSHServer = DummySSHServer

    def setUp(self):
        super().setUp()
        # Create dummy SSH server
        self.ssh_server = self.SSHServer(self.files.joinpath('ssh_host_key'))
        patch_ssh_connect = patch.object(paramiko.SSHClient, 'connect',
                                         autospec=True,
                                         side_effect=self.ssh_server.connect)
        patch_ssh_connect.start()
        self.addCleanup(patch_ssh_connect.stop)

    def tearDown(self):
        # Check for exceptions that have been caught and converted to issues
        self.assertEqual(len(self.gateway.issue_ids), 0)
        super().tearDown()
        del self.ssh_server


class EdiGatewayCommonCase(EdiGatewayCase):
    """EDI gateway tests that do not use the connection model"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        EdiTransfer = cls.env['edi.transfer']
        EdiDocument = cls.env['edi.document']

        # Create transfer
        cls.xfer = EdiTransfer.create({
            'gateway_id': cls.gateway.id,
        })

        # Create document
        cls.doc = EdiDocument.create({
            'name': "Test document",
            'doc_type_id': cls.doc_type_unknown.id,
            'transfer_id': cls.xfer.id,
        })

    def test01_action_view_cron(self):
        """Test view scheduled jobs"""
        IrCron = self.env['ir.cron']
        action = self.gateway.action_view_cron()
        self.assertEqual(len(IrCron.search(action['domain'])), 0)
        cron = IrCron.with_context(action['context']).create({
            'name': "Test cron job",
        })
        self.assertIn(cron, self.gateway.cron_ids)
        self.assertEqual(self.gateway.cron_count, 1)
        action = self.gateway.action_view_cron()
        self.assertEqual(len(IrCron.search(action['domain'])), 1)

    def test02_action_view_paths(self):
        """Test view paths"""
        EdiPath = self.env['edi.gateway.path']
        action = self.gateway.action_view_paths()
        self.assertEqual(len(EdiPath.search(action['domain'])),
                         self.gateway.path_count)
        path = EdiPath.with_context(action['context']).create({
            'name': "Brand new path!",
            'path': "Middle of nowhere",
        })
        self.assertIn(path, self.gateway.path_ids)
        action = self.gateway.action_view_paths()
        self.assertIn(path, EdiPath.search(action['domain']))

    def test03_action_view_transfers(self):
        """Test view transfers"""
        EdiTransfer = self.env['edi.transfer']
        action = self.gateway.action_view_transfers()
        self.assertEqual(EdiTransfer.search(action['domain']), self.xfer)
        self.assertEqual(len(EdiTransfer.search(action['domain'])),
                         self.gateway.transfer_count)

    def test04_action_view_docs(self):
        """Test view documents"""
        EdiDocument = self.env['edi.document']
        action = self.gateway.action_view_docs()
        self.assertEqual(EdiDocument.search(action['domain']), self.doc)
        self.assertEqual(len(EdiDocument.search(action['domain'])),
                         self.gateway.doc_count)

    def test05_ssh_connect(self):
        """Test connect to SSH server"""
        self.gateway.server = 'dummy'
        self.gateway.username = 'user'
        self.gateway.password = 'pass'
        ssh = self.gateway.ssh_connect()
        ssh.close()
        self.assertEqual(self.gateway.ssh_host_fingerprint,
                         'e3:32:6e:5c:ee:47:58:2d:bb:f1:d0:3b:0e:c4:55:a0')


class EdiGatewayConnectionCase(EdiGatewayCase):
    """Base test class for EDI gateway connection models"""

    @contextmanager
    def patch_paths(self, _path_files):
        """Patch EDI paths to include specified test files

        This is a context manager; the patch will be removed when the
        context exits.
        """
        yield

    def assertSent(self, _ctx, _path_files):
        """Assert that specified test files were sent"""
        pass

    @skipUnlessCanInitiate
    def test01_action_test(self):
        """Test the ability to test the connection"""
        old_messages = self.gateway.message_ids
        self.gateway.action_test()
        new_messages = self.gateway.message_ids - old_messages
        self.assertEqual(len(new_messages), 1)

    @skipUnlessCanInitiate
    def test02_transfer_no_paths(self):
        """Test transfer (with no paths defined)"""
        self.gateway.path_ids.unlink()
        old_transfers = self.gateway.transfer_ids
        transfer = self.gateway.do_transfer()
        new_transfers = self.gateway.transfer_ids - old_transfers
        self.assertIn(transfer, new_transfers)
        self.assertEqual(len(new_transfers), 1)

    @skipUnlessCanInitiate
    def test03_action_transfer_no_paths(self):
        """Test transfer action (with no paths defined)"""
        self.gateway.path_ids.unlink()
        self.assertTrue(self.gateway.action_transfer())

    @skipUnlessCanInitiate
    @skipUnlessCanReceive
    def test04_transfer_receive(self):
        """Test receiving attachments"""
        with self.patch_paths({self.path_receive: ['hello_world.txt']}):
            transfer = self.gateway.with_context({
                'default_allow_process': False,
            }).do_transfer()
            self.assertEqual(len(transfer.input_ids), 1)
            self.assertEqual(len(transfer.output_ids), 0)
            self.assertAttachment(transfer.input_ids, 'hello_world.txt')
        with self.patch_paths({self.path_receive: ['hello_world.txt']}):
            transfer = self.gateway.with_context({
                'default_allow_process': False,
            }).do_transfer()
            self.assertEqual(len(transfer.input_ids), 0)
            self.assertEqual(len(transfer.output_ids), 0)

    @skipUnlessCanInitiate
    @skipUnlessCanSend
    def test05_transfer_send(self):
        """Test sending attachments"""
        EdiDocument = self.env['edi.document']
        today = fields.Datetime.now()
        doc = EdiDocument.create({
            'name': "ToDo list",
            'doc_type_id': self.doc_type_unknown.id,
            'state': 'done',
            'prepare_date': today,
            'execute_date': today,
        })
        attachment = self.create_output_attachment(doc, 'hello_world.txt')
        with self.patch_paths({}) as ctx:
            transfer = self.gateway.do_transfer()
            self.assertEqual(len(transfer.input_ids), 0)
            self.assertEqual(len(transfer.output_ids), 1)
            self.assertIn(attachment, transfer.output_ids)
            self.assertSent(ctx, {self.path_send: ['hello_world.txt']})
        with self.patch_paths({self.path_send: ['hello_world.txt']}) as ctx:
            transfer = self.gateway.do_transfer()
            self.assertEqual(len(transfer.input_ids), 0)
            self.assertEqual(len(transfer.output_ids), 0)
            self.assertSent(ctx, {})

    @skipUnlessCanInitiate
    @skipUnlessCanReceive
    def test06_receive_age_window(self):
        """Test receive age window"""
        old_file = EdiTestFile('hello_world.txt', age=timedelta(hours=36))
        with self.patch_paths({self.path_receive: [old_file]}):
            self.path_receive.age_window = 24
            transfer = self.gateway.with_context({
                'default_allow_process': False,
            }).do_transfer()
            self.assertEqual(len(transfer.input_ids), 0)
        with self.patch_paths({self.path_receive: [old_file]}):
            self.path_receive.age_window = 48
            transfer = self.gateway.with_context({
                'default_allow_process': False,
            }).do_transfer()
            self.assertEqual(len(transfer.input_ids), 1)
            self.assertAttachment(transfer.input_ids, 'hello_world.txt')

    @skipUnlessCanInitiate
    def test07_safety_catch(self):
        """Test safety catch"""
        EdiTransfer = self.env['edi.transfer']
        self.gateway.path_ids.unlink()
        with patch.object(config, 'get_misc', autospec=True) as mock_get_misc, \
             patch.object(EdiTransfer.__class__, 'do_transfer',
                          autospec=True) as mock_do_transfer:

            # No safety option defined
            self.gateway.safety = None
            self.assertTrue(self.gateway.action_transfer())
            self.assertTrue(mock_do_transfer.called)
            mock_get_misc.reset_mock()
            mock_do_transfer.reset_mock()

            # Safety option defined, not present in configuration file
            with self.assertRaisesIssue(self.gateway):
                mock_get_misc.return_value = None
                self.gateway.safety = 'is_production'
                self.assertFalse(self.gateway.action_transfer())
                self.assertFalse(mock_do_transfer.called)
                mock_get_misc.assert_called_once_with('edi', 'is_production')
                mock_get_misc.reset_mock()
                mock_do_transfer.reset_mock()

            # Safety option defined, false value in configuration file
            with self.assertRaisesIssue(self.gateway):
                mock_get_misc.return_value = False
                self.gateway.safety = 'customer.allow_edi'
                self.assertFalse(self.gateway.action_transfer())
                self.assertFalse(mock_do_transfer.called)
                mock_get_misc.assert_called_once_with('customer', 'allow_edi')
                mock_get_misc.reset_mock()
                mock_do_transfer.reset_mock()

            # Safety option defined, true value in configuration file
            mock_get_misc.return_value = True
            self.gateway.safety = 'enabled'
            self.assertTrue(self.gateway.action_transfer())
            self.assertTrue(mock_do_transfer.called)
            mock_get_misc.assert_called_once_with('edi', 'enabled')
            mock_get_misc.reset_mock()
            mock_do_transfer.reset_mock()

    @skipUnlessCanInitiate
    @skipUnlessCanReceive
    def test08_transfer_receive_processing(self):
        """Test receiving attachments and processing"""
        EdiDocumentType = self.env['edi.document.type']
        IrModel = self.env['ir.model']
        doc_type = EdiDocumentType.create({
            'name': "Test EDI document",
            'model_id': IrModel._get_id('edi.document.model'),
        })
        self.path_receive.doc_type_ids = [doc_type.id]
        with self.patch_paths({self.path_receive: ['hello_world.txt']}):
            transfer = self.gateway.do_transfer()
            self.assertEqual(len(transfer.input_ids), 1)
            self.assertEqual(len(transfer.output_ids), 0)
            self.assertAttachment(transfer.input_ids, 'hello_world.txt')

    @skipUnlessCanInitiate
    def test09_action_test_fail(self):
        """Test the ability to test the connection"""
        Model = self.env[self.gateway.model_id.model]
        with patch.object(Model.__class__, 'connect', autospec=True,
                          side_effect=Exception):
            with self.assertRaisesIssue(self.gateway, exception=Exception):
                old_messages = self.gateway.message_ids
                self.gateway.action_test()
                new_messages = self.gateway.message_ids - old_messages
                # two new messages: one for the error and one for its traceback
                self.assertEqual(len(new_messages), 2)


class EdiGatewayFileSystemCase(EdiGatewayConnectionCase):
    """Base test case for filesystem-like EDI gateways"""

    Context = namedtuple('EdiGatewayFileSystemCaseContext',
                         ['temppath', 'subpaths', 'path_files'])

    @property
    def path_subdirs(self):
        """Mapping from EDI paths to temporary subdirectories

        By default, the ``edi.gateway.path.path`` attribute is used as
        the subdirectory name.
        """
        return {path: path.path for path in self.gateway.path_ids}

    @contextmanager
    def patch_paths(self, path_files):
        """Patch EDI paths to include specified test files

        Create a temporary directory containing subdirectories for
        each defined path on the EDI gateway, and populate these
        subdirectories with the specified test files.

        This is a context manager; the temporary directory will be
        deleted when the context exits.
        """

        # Duplicate original EDI path -> files mapping for later comparison
        path_files = {path: list(files) for path, files in path_files.items()}

        # Create and populate temporary directory
        with tempfile.TemporaryDirectory() as tempdir:

            # Create subdirectory for each defined EDI path
            temppath = pathlib.Path(tempdir)
            subpaths = {path: temppath.joinpath(subdir)
                        for path, subdir in self.path_subdirs.items()}
            for subpath in subpaths.values():
                subpath.mkdir(parents=True, exist_ok=True)

            # Copy in specified test files
            for path, files in path_files.items():
                for file in files:
                    src = self.files.joinpath(file)
                    dst = subpaths[path].joinpath(file)
                    self.assertFalse(dst.exists())
                    shutil.copy(str(src), str(dst))
                    if hasattr(file, 'mtime'):
                        mtime = file.mtime.timestamp()
                        os.utime(str(dst), times=(mtime, mtime))

            yield self.Context(temppath, subpaths, path_files)

    def assertSent(self, ctx, path_files):
        """Assert that specified test files were sent

        The contents of the temporary directory will be compared
        against the expected contents.
        """
        expected = {
            path.name: set((file, self.files.joinpath(file).read_bytes())
                           for file in (set(ctx.path_files.get(path, ())) |
                                        set(path_files.get(path, ()))))
            for path in ctx.subpaths
        }
        actual = {
            path.name: set((file.name, file.read_bytes())
                           for file in subpath.iterdir())
            for path, subpath in ctx.subpaths.items()
        }
        self.assertEqual(actual, expected)
