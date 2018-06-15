import os
from time import time
from collections import namedtuple
from unittest.mock import patch


class DummySftpConnection(object):
    """Dummy SFTP server connection

    This mocks up a paramiko.SFTPClient object, providing access to
    specified local test files.
    """

    def __init__(self, inputs=None, outputs=None):
        self.inputs = inputs or {}
        self.outputs = outputs or {}
        self.actual = {k: [] for k in self.outputs}
        # the following directories need to be defined in a subclass
        # at a directory level where will be handled the test files
        # tests/files/out/
        self.directory = None
        self.output_directory = None

    def listdir_attr(self, path):
        """List directory contents (with file sizes)"""
        dirent = namedtuple('dirent', ['filename', 'st_size', 'st_mtime'])
        if path in self.inputs:
            for filename in self.inputs[path]:
                stat = os.stat(os.path.join(self.directory, filename))
                yield dirent(filename=filename, st_size=stat.st_size,
                             st_mtime=stat.st_mtime)
        else:
            for filename in os.listdir(self.output_directory):
                if path in self.outputs and filename in self.outputs[path]:
                    continue
                stat = os.stat(os.path.join(self.output_directory, filename))
                yield dirent(filename=filename, st_size=stat.st_size,
                             st_mtime=time())

    def file(self, filepath, mode):
        """Access file"""
        path, filename = os.path.split(filepath)
        if 'w' in mode:
            self.actual[path].append(filename)
            return open(os.path.join(self.output_directory, filename), mode)
        else:
            return open(os.path.join(self.directory, filename), mode)

    def rename(self, src_filepath, dst_filepath):
        """Rename file"""
        src_path, src_filename = os.path.split(src_filepath)
        dst_path, dst_filename = os.path.split(dst_filepath)
        self.actual[src_path].remove(src_filename)
        self.actual[dst_path].append(dst_filename)
        os.rename(os.path.join(self.output_directory, src_filename),
                  os.path.join(self.output_directory, dst_filename))

    def close(self):
        return True

    def get_channel(self):
        class chan(object):
            @staticmethod
            def settimeout(*args, **kwargs):
                pass
        return chan


class UdesDummySftpConnection(DummySftpConnection):

    def __init__(self, test_class,  inputs=None, outputs=None,
                 in_folder='files', out_folder='out', side_effect=None):
        super(UdesDummySftpConnection, self).__init__(inputs, outputs)
        # override directory value to have the files for testing in the
        # current module
        self.directory = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), in_folder
        )
        self.output_directory = os.path.join(self.directory, out_folder)
        self._test_class = test_class
        self._side_effect = side_effect

    def __enter__(self, *args, **kwargs):
        patch_sftp = patch('odoo.addons.edi.models.edi_connection_sftp.'
                           'SFTPOnlyClient.from_transport',
                           autospec=True,
                           return_value=self,
                           side_effect=self._side_effect)

        patch_ssh = patch('paramiko.SSHClient.connect', autospec=True)

        self._test_class.patched_sftp = patch_sftp.start()
        self._test_class.addCleanup(patch_sftp.stop)
        self._test_class.patched_ssh = patch_ssh.start()
        self._test_class.addCleanup(patch_ssh.stop)

        return self

    def __exit__(self, *args, **kwargs):
        self._test_class.doCleanups()
        return False
