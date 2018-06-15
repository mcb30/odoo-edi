from . import common
import os.path

from odoo import fields


class TestEDIGateway(common.BaseEDI):

    @classmethod
    def setUpClass(cls):
        super(TestEDIGateway, cls).setUpClass()

    def setUp(self):
        super(TestEDIGateway, self).setUp()

    def _test_action_test(self, gateway):
        """ Test action test to check connection is fine """

        old_messages = gateway.message_ids
        gateway.action_test()
        new_message = gateway.message_ids - old_messages
        self.assertEqual(len(new_message), 1)
        self.assertIn("Connection tested successfully", new_message.body)

    def _test_do_transfer_no_path(self, gateway, conn=None):
        """ Test do transfer with no path, which means a transfer
            is created but nothing received
        """
        old_transfers = gateway.transfer_ids
        transfer = gateway.do_transfer(conn=conn)
        new_transfer = gateway.transfer_ids - old_transfers
        self.assertEqual(new_transfer, transfer)
        self.assertEqual(len(transfer.issue_ids), 0)

    def _test_action_transfer_no_path(self, gateway):
        """ Test action transfer with no path, which means a transfer
            is created but nothing received and no issues raised
        """

        old_transfers = gateway.transfer_ids
        no_issues = gateway.action_transfer()
        new_transfer = gateway.transfer_ids - old_transfers
        self.assertEqual(len(new_transfer), 1)
        self.assertTrue(no_issues)

    def _test_do_transfer_receive(self, gateway, conn=None):
        """ Test do transfer with input path, which means a transfer
            is created and a file is received
        """
        # first transfer receives dummy file
        old_transfers = gateway.transfer_ids
        transfer = gateway.do_transfer(conn=conn)
        new_transfer = gateway.transfer_ids - old_transfers
        self.assertEqual(new_transfer, transfer)
        issue = transfer.issue_ids

        self.assertEqual(len(issue), 1)
        self.assertIn('Unknown document type', issue.name)
        self.assertEqual(len(transfer.input_ids), 1)

        # second transfer ignores dummy file
        old_transfers = gateway.transfer_ids
        transfer = gateway.do_transfer(conn=conn)
        new_transfer = gateway.transfer_ids - old_transfers
        self.assertEqual(new_transfer, transfer)
        self.assertEqual(len(transfer.input_ids), 0)

    def _test_do_transfer_receive_old_file_ignored(self, gateway, conn=None):
        """ Test do transfer with input path to an old file,
            which means a transfer is created but nothing received
        """

        old_transfers = gateway.transfer_ids
        transfer = gateway.do_transfer(conn=conn)
        new_transfer = gateway.transfer_ids - old_transfers
        self.assertEqual(new_transfer, transfer)
        self.assertEqual(len(transfer.input_ids), 0)

    def _test_do_transfer_send(self, gateway, conn=None):
        """ Test do transfer with output path. Create a document
            with two attachments: one matching the pattern and one
            don't.
        """

        doc = self._create_document(self.document_type_unknown)
        # bypass prep and exec
        doc.state = 'done'
        doc.execute_date = fields.Datetime.now()

        # Add one attachment to the  document that matches the pattern
        file_name = self._generate_file_name(prefix='test_', suffix='.out')
        attachment = self._create_attachment(doc, "Hello World!!",
                                             file_name, attach_type='output')
        self.assertIn(attachment, doc.output_ids)

        # Add another attachment to the  document that does not match
        # the pattern
        file_name = self._generate_file_name(prefix='test_')
        attachment = self._create_attachment(doc, "Hello World!!",
                                             file_name, attach_type='output')
        self.assertIn(attachment, doc.output_ids)
        # document has two attachments
        self.assertEqual(len(doc.output_ids), 2)

        old_transfers = gateway.transfer_ids
        transfer = gateway.do_transfer(conn=conn)
        new_transfer = gateway.transfer_ids - old_transfers
        self.assertEqual(new_transfer, transfer)
        # transfer has one attachment
        self.assertEqual(len(transfer.output_ids), 1)


from base64 import b64encode

class TestEDIXMLRPCGateway(TestEDIGateway):

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


class TestEDILocalGateway(TestEDIGateway):

    @classmethod
    def setUpClass(cls):
        super(TestEDILocalGateway, cls).setUpClass()

    def setUp(self):
        super(TestEDILocalGateway, self).setUp()

    def test01_gateway_action_test(self):

        gateway = self._create_local_gateway()
        self._create_local_path(gateway=gateway,
                                allow_send=False)
        self._test_action_test(gateway)

    def test02_gateway_do_transfer_no_path(self):

        gateway = self._create_local_gateway()
        self._test_do_transfer_no_path(gateway)

    def test03_gateway_do_transfer_receive(self):

        gateway = self._create_local_gateway()
        self._create_local_path(gateway=gateway,
                                allow_send=False)
        self._test_do_transfer_receive(gateway)

    def test04_gateway_do_transfer_receive_old_file_ignored(self):

        gateway = self._create_local_gateway()
        self._create_local_path(gateway=gateway,
                                touch_files=False,
                                folder='files/old',
                                age_window=0.01)
        self._test_do_transfer_receive_old_file_ignored(gateway)

    def test05_gateway_do_transfer_send(self):

        gateway = self._create_local_gateway()
        self._create_local_path(gateway=gateway,
                                folder='files/out',
                                glob='*.out',
                                allow_receive=False,
                                doc_type_ids=[(6, 0, [self.document_type_unknown.id])],
                                )
        self._test_do_transfer_send(gateway)

    def test06_gateway_action_transfer_no_path(self):

        gateway = self._create_local_gateway()
        self._test_action_transfer_no_path(gateway)
