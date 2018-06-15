from .test_gateway import TestEDIGateway

from .mock_connections import UdesDummySftpConnection
from ..models.edi_gateway import EdiAutoAddHostKeyPolicy

import os
from unittest.mock import patch
from paramiko import SSHClient, SSHException, BadHostKeyException
from odoo.exceptions import UserError
from odoo.tools import config as Odoo_config
from collections import namedtuple
from paramiko.pkey import PKey
import base64


class TestEDISFTPGateway(TestEDIGateway):

    @classmethod
    def _create_sftp_gateway(cls, **kwargs):
        model = cls.env.ref('edi.model_edi_connection_sftp')
        data = {
          'name': 'Test SFTP Gateway',
          'model_id': model.id,
        }
        data.update(kwargs)
        return cls._create_gateway(**data)

    def _patch_sftp_connection(self, collect_inputs=True, **kwargs):
        data = {
            'test_class': self,
            'inputs': {'sftp:in': []},
            'outputs': {'sftp:out': []},
        }

        data.update(kwargs)

        conn = UdesDummySftpConnection(**data)

        if collect_inputs:
            key = list(conn.inputs.keys())[0]
            conn.inputs[key].extend(
                (fname
                 for fname in os.listdir(conn.directory)
                 if os.path.isfile(os.path.join(conn.directory, fname)))
            )

        return conn

    @classmethod
    def _create_sftp_path(cls, gateway, folder='in', **kwargs):
        directory = ':'.join([
            'sftp', folder
        ])

        data = {
            'name': 'stfp path for %s' % gateway.name,
            'gateway_id': gateway.id,
            'glob': '*.txt',
            'path': directory,
            'age_window': 24,
        }

        if kwargs:
            data.update(kwargs)

        return cls._create_path(**data)

    def test01_gateway_action_test(self):

        gateway = self._create_sftp_gateway()
        self._create_local_path(gateway=gateway,
                                allow_send=False)
        with self._patch_sftp_connection():
            self._test_action_test(gateway)

    def test02_gateway_do_transfer_no_path(self):

        gateway = self._create_sftp_gateway()
        with self._patch_sftp_connection():
            self._test_do_transfer_no_path(gateway=gateway)

    def test03_gateway_do_transfer_receive(self):

        gateway = self._create_sftp_gateway()
        path = self._create_sftp_path(gateway=gateway,
                                      allow_send=False)
        with self._patch_sftp_connection() as conn:
            self._touch_files_in_path(conn.directory, path.glob)
            self._test_do_transfer_receive(gateway=gateway)

    def test04_gateway_do_transfer_receive_old_file_ignored(self):

        gateway = self._create_sftp_gateway()
        self._create_sftp_path(gateway=gateway,
                               allow_send=False,
                               folder='files/old',
                               age_window=0.000001)
        with self._patch_sftp_connection(inputs={'sftp:files/old': []},
                                         in_folder='files/old'):
            self._test_do_transfer_receive_old_file_ignored(gateway=gateway)

    def test05_gateway_do_transfer_send(self):
        gateway = self._create_sftp_gateway()
        dt_ids = [(6, 0, [self.document_type_unknown.id])]

        self._create_sftp_path(gateway=gateway,
                               folder='out',
                               glob='*.out',
                               allow_receive=False,
                               doc_type_ids=dt_ids,
                               )

        with self._patch_sftp_connection(collect_inputs=False):
            self._test_do_transfer_send(gateway=gateway)

    def test06_action_transfer_no_path(self):
        gateway = self._create_sftp_gateway()
        with self._patch_sftp_connection():
            self._test_action_transfer_no_path(gateway)

    def test07_ssh_con(self):
        gateway = self._create_sftp_gateway(username='bob',
                                            config_password=True,
                                            timeout=60)

        patched_config = patch.object(Odoo_config, 'get_misc', autospec=True,
                                      return_value='bobs_password')
        patch_connect = patch.object(SSHClient, 'connect', autospec=True)
        with patched_config, patch_connect:
                gateway.ssh_connect()

    def test08_ssh_con_error(self):
        gateway = self._create_sftp_gateway(username='bob',
                                            password='bobs_password',
                                            timeout=60)
        patch_ssh_connect = patch.object(SSHClient, 'connect', autospec=True,
                                         side_effect=SSHException)

        with self.assertRaises(UserError), patch_ssh_connect:
                gateway.ssh_connect()

    def test09_gateway_do_passing_connection(self):

        gateway = self._create_sftp_gateway()
        path = self._create_sftp_path(gateway=gateway,
                                      allow_send=False)
        conn = self._patch_sftp_connection()
        self._touch_files_in_path(conn.directory, path.glob)
        self._test_do_transfer_receive(gateway=gateway,
                                       conn=conn)

    def test10_gateway_do_passing_connection_error(self):
        EdiTransfer = self.env['edi.transfer']

        gateway = self._create_sftp_gateway()
        conn = self._patch_sftp_connection()

        patch_conn_error = patch.object(EdiTransfer.__class__,
                                        'do_transfer',
                                        side_effect=Exception)

        with self.assertRaises(Exception), patch_conn_error:
            self._test_do_transfer_no_path(gateway=gateway,
                                           conn=conn)

    def test11_action_view_cron(self):
        gateway = self._create_sftp_gateway()
        actual = gateway.action_view_cron()

        expected = {}
        expected['domain'] = [('state', '=', 'edi'),
                              ('edi_gateway_id', '=', gateway.id)]
        expected['context'] = {
            'default_model_id': gateway.env['ir.model']._get_id('edi.gateway'),
            'default_state': 'edi',
            'default_edi_gateway_id': gateway.id,
            'default_numbercall': -1,
            'create': True
        }
        self.assertIsSubset(expected, actual)

    def test12_action_view_cron(self):
        gateway = self._create_sftp_gateway()
        actual = gateway.action_view_paths()

        expected = {}
        expected['domain'] = [('gateway_id', '=', gateway.id)]
        expected['context'] = {'default_gateway_id': gateway.id}
        self.assertIsSubset(expected, actual)

    def test13_action_view_transfers(self):
        gateway = self._create_sftp_gateway()
        actual = gateway.action_view_transfers()

        expected = {}
        expected['domain'] = [('gateway_id', '=', gateway.id)]
        self.assertIsSubset(expected, actual)

    def test14_action_view_docs(self):
        gateway = self._create_sftp_gateway()
        actual = gateway.action_view_docs()

        expected = {}
        expected['domain'] = [('gateway_id', '=', gateway.id)]
        expected['context'] = {'create': False}
        self.assertIsSubset(expected, actual)

    def test15_gateway_action_test_error(self):

        gateway = self._create_sftp_gateway()
        patch_conn = self._patch_sftp_connection(side_effect=Exception)
        with self.assertRaises(Exception), patch_conn:
            self._test_action_test(gateway)

    def test16_send_twice(self):
        gateway = self._create_sftp_gateway(timeout=60)
        dt_ids = [(6, 0, [self.document_type_unknown.id])]

        self._create_sftp_path(gateway=gateway,
                               folder='out',
                               glob='*.out',
                               allow_receive=False,
                               doc_type_ids=dt_ids,
                               )
        with self._patch_sftp_connection(collect_inputs=False):
            self._test_do_transfer_send(gateway=gateway)
        with self._patch_sftp_connection(collect_inputs=False):
            self._test_do_transfer_send(gateway=gateway,
                                        expected_outputs=0)

    def test16_missing_host_key_policy(self):
        HostKeyEntry = namedtuple('HostKeyEntry', ['hostnames', 'key'])
        entry = HostKeyEntry(hostnames=['Host123'],
                             key=PKey())

        patch_from_line = patch('paramiko.hostkeys.HostKeyEntry.from_line',
                                return_value=entry)

        EdiGateway = self.env['edi.gateway']
        patch_fingerprint = patch.object(
            EdiGateway.__class__,
            '_compute_ssh_host_fingerprint',
            autospec=True,
            return_value=base64.b64encode(b'abc:abc:abc')
        )
        assertRaises = self.assertRaises(BadHostKeyException)
        with assertRaises, patch_from_line, patch_fingerprint:
            gateway = self._create_sftp_gateway(
                                                ssh_host_key=base64.b64encode(b'abc:def:ghi'))
            policy = EdiAutoAddHostKeyPolicy(gateway)
            policy.missing_host_key(None, 'BadHost', PKey())

    def test17_missing_host_key_policy2(self):
        class MockKey(object):
            @staticmethod
            def to_line():
                return 'IWalkTheLine'

        patch_entry = patch('paramiko.hostkeys.HostKeyEntry', return_value=MockKey)
        gateway = self._create_sftp_gateway()
        policy = EdiAutoAddHostKeyPolicy(gateway)
        with patch_entry:
            policy.missing_host_key(None, 'BadHost', PKey())
