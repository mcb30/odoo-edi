import os
from time import time
from collections import namedtuple


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

    def close(self):
        return True


class UdesDummySftpConnection(DummySftpConnection):
    def __init__(self, inputs=None, outputs=None,
                 in_folder='files', out_folder='out'):
        super(UdesDummySftpConnection, self).__init__(inputs, outputs)
        # override directory value to have the files for testing in the
        # current module
        self.directory = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), in_folder
        )
        self.output_directory = os.path.join(self.directory, out_folder)
