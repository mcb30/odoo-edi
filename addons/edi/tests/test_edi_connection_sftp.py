"""EDI SFTP connection tests"""

import base64
from contextlib import contextmanager
import os
import paramiko
from . import test_edi_gateway


class DummySFTPHandle(paramiko.SFTPHandle):
    """Dummy SFTP file"""

    def __init__(self, file, flags=0):
        super().__init__(flags=flags)
        self.readfile = file
        self.writefile = file


class DummySFTPServer(paramiko.SFTPServerInterface):
    """Dummy SFTP server"""

    def __init__(self, server):
        super().__init__(server)
        self.root = server.root

    def list_folder(self, path):
        """List directory contents"""
        return [paramiko.SFTPAttributes.from_stat(x.stat(), filename=x.name)
                for x in self.root.joinpath(path).iterdir()]

    def open(self, path, flags, attr):
        """Open file"""
        mode = 'wb' if flags & os.O_WRONLY else 'rb'
        file = self.root.joinpath(path).open(mode=mode)
        return DummySFTPHandle(file, flags=flags)

    def rename(self, oldpath, newpath):
        """Rename file"""
        self.root.joinpath(oldpath).rename(self.root.joinpath(newpath))
        return paramiko.SFTP_OK


class DummySSHServer(test_edi_gateway.DummySSHServer):
    """Dummy SSH server with SFTP support"""

    root = None
    """Root directory"""

    def create_transport(self, sock):
        transport = super().create_transport(sock)
        transport.set_subsystem_handler('sftp', paramiko.SFTPServer,
                                        DummySFTPServer)
        return transport


class TestEdiConnectionSFTP(test_edi_gateway.EdiGatewayFileSystemCase):
    """EDI SFTP connection tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        IrModel = cls.env['ir.model']
        cls.gateway.write({
            'name': "Test SFTP gateway",
            'model_id': IrModel._get_id('edi.connection.sftp'),
            'server': 'dummy',
            'username': 'user',
            'password': 'pass',
            'ssh_host_key': base64.b64encode(
                cls.files.joinpath('ssh_known_hosts').read_bytes()
            ),
        })
        cls.path_receive.path = "receive"
        cls.path_send.path = "send"
        cls.SSHServer = DummySSHServer

    @contextmanager
    def patch_paths(self, path_files):
        """Patch EDI paths to include specified test files

        A dummy SFTP server is instantiated providing access to a
        temporary local directory.
        """
        with super().patch_paths(path_files) as ctx:
            try:
                self.ssh_server.root = ctx.temppath
                yield ctx
            finally:
                self.ssh_server.root = None
