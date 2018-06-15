"""EDI XMLRPC connection tests"""

from .test_gateway import TestEDIGateway
from base64 import b64encode
import os.path


class TestEDIXMLRPCGateway(TestEDIGateway):
    """EDI XMLRPC connection tests"""

    @classmethod
    def setUpClass(cls):
        super(TestEDIXMLRPCGateway, cls).setUpClass()

    def setUp(self):
        super(TestEDIXMLRPCGateway, self).setUp()

    @classmethod
    def _create_xmlrpc_gateway(cls):
        model = cls.env.ref('edi.model_edi_connection_xmlrpc')
        return cls._create_gateway(name='Test XMLRPC Gateway',
                                   model_id=model.id)

    @classmethod
    def _create_xmlrpc_path(cls, gateway):
        data = {
            'name': 'Local path for %s' % gateway.name,
            'gateway_id': gateway.id,
            'glob': '*.txt',
            'path': 'files',
            'age_window': 24,
        }
        return cls._create_path(**data)

    @classmethod
    def _create_xmlrpc_conn(cls):
        prf_filename = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'files', 'hello_world.txt')

        conn = {'files': [{
            'name': 'hello_world.txt',
            'data': b64encode(open(prf_filename, 'rb').read()),
        }]}

        return conn

    def test02_gateway_do_transfer_no_path(self):

        gateway = self._create_xmlrpc_gateway()
        conn = self._create_xmlrpc_conn()
        self._test_do_transfer_no_path(gateway, conn=conn)

    def test03_gateway_do_transfer_receive(self):

        gateway = self._create_xmlrpc_gateway()
        path = self._create_xmlrpc_path(gateway)

        conn = self._create_xmlrpc_conn()

        self._test_do_transfer_receive(gateway, conn=conn)


