"""EDI xmlrpc connection tests"""

from contextlib import contextmanager
from . import test_edi_gateway
from base64 import b64encode
from xmlrpc.client import Binary


class TestEdiConnectionXmlrpc(test_edi_gateway.EdiGatewayConnectionCase):
    """EDI xmlrpc connection tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        IrModel = cls.env['ir.model']
        cls.gateway.write({
            'name': "Test XMLRPC gateway",
            'model_id': IrModel._get_id('edi.connection.xmlrpc'),
        })
        cls.path_receive.path = "receive"
        cls.path_send.path = "send"

    def setUp(self):
        super(TestEdiConnectionXmlrpc, self).setUp()
        # create empty xmlrpc connection
        self.conn = {self.path_receive.path: [], self.path_send.path: []}

    @contextmanager
    def patch_paths(self, path_files):
        """Patch EDI paths to include specified test files
        """
        self.conn = {path.path:
                     [{'name': str(file),
                       'data': Binary(b64encode(self.files.joinpath(file).read_bytes())),
                       'size': self.files.joinpath(file).stat().st_size}
                      for file in files]
                     for path, files in path_files.items()}
        yield
        self.conn = None