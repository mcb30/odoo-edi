from .test_gateway import TestEDIGateway

from ..models.edi_connection_sftp import EdiConnectionSFTP
from .mock_connections import UdesDummySftpConnection

from unittest.mock import patch
import os


class TestEDISFTPGateway(TestEDIGateway):

    @classmethod
    def _create_sftp_gateway(cls):
        model = cls.env.ref('edi.model_edi_connection_sftp')
        return cls._create_gateway(name='Test SFTP Gateway',
                                   model_id=model.id)

    @staticmethod
    def _get_sftp_connection(collect_inputs=True, **kwargs):
        data = {
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

        patcher = patch.object(EdiConnectionSFTP, 'connect',
                               autospec=True,
                               return_value=self._get_sftp_connection())

        self.patched_send = patcher.start()
        self.addCleanup(patcher.stop)

        gateway = self._create_sftp_gateway()
        self._create_local_path(gateway=gateway,
                                allow_send=False)
        self._test_action_test(gateway)

    def _test02_gateway_do_transfer_no_path(self):

        gateway = self._create_sftp_gateway()
        conn = self._get_sftp_connection()
        self._test_do_transfer_no_path(gateway=gateway,
                                       conn=conn)

    def _test03_gateway_do_transfer_receive(self):

        gateway = self._create_sftp_gateway()
        path = self._create_sftp_path(gateway=gateway,
                                      allow_send=False)
        conn = self._get_sftp_connection()
        self._touch_files_in_path(conn.directory, path.glob)
        self._test_do_transfer_receive(gateway=gateway,
                                       conn=conn)

    def _test04_gateway_do_transfer_receive_old_file_ignored(self):

        gateway = self._create_sftp_gateway()
        self._create_sftp_path(gateway=gateway,
                               touch_files=False,
                               allow_send=False,
                               folder='files/old',
                               age_window=0.000001)
        conn = self._get_sftp_connection(inputs={'sftp:files/old': []},
                                         in_folder='files/old')
        self._test_do_transfer_receive_old_file_ignored(gateway=gateway,
                                                        conn=conn)

    def _test05_gateway_do_transfer_send(self):
        gateway = self._create_sftp_gateway()
        dt_ids = [(6, 0, [self.document_type_unknown.id])]

        self._create_sftp_path(gateway=gateway,
                               folder='out',
                               glob='*.out',
                               allow_receive=False,
                               doc_type_ids=dt_ids,
                               )
        conn = self._get_sftp_connection(collect_inputs=False)
        self._test_do_transfer_send(gateway=gateway,
                                    conn=conn)