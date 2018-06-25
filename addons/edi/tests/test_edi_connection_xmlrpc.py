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

    def _test001_xmlrpc_transfer(self):
        """Test xmlrpc transfer"""
        file = "hello_world.txt"
        receive_data = [
            {'name': file,
             'data': Binary(b64encode(self.files.joinpath(file).read_bytes())),
             'size': self.files.joinpath(file).stat().st_size}
        ]

        res = self.gateway.xmlrpc_transfer(receive=receive_data)
        self.assertEqual(len(res['docs']), 1)
        self.assertEqual(len(res['errors']), 1)
        self.gateway.issue_ids.unlink()

    def test002_send_ouputs(self):
        """Test send outputs"""
        EdiTransfer = self.env['edi.transfer']
        EdiDocument = self.env['edi.document']

        # Create transfer
        self.xfer = EdiTransfer.create({
            'gateway_id': self.gateway.id,
        })

        # Create document
        self.doc = EdiDocument.create({
            'name': "Test document",
            'doc_type_id': self.doc_type_unknown.id,
            'transfer_id': self.xfer.id,
            'state': 'done',
        })
        self.create_output_attachment(self.doc, 'hello_world.txt')
        self.xfer.send_outputs(self.conn)
        self.assertEqual(len(self.conn[self.path_send.path]), 1)
        self.assertEqual(len(self.xfer.output_ids), 1)
        self.assertAttachment(self.xfer.output_ids, "hello_world.txt")
