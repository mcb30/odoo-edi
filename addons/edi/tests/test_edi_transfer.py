"""EDI transfer tests"""

from .common import EdiCase


class TestEdiTransfer(EdiCase):
    """EDI transfer tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        IrModel = cls.env["ir.model"]
        EdiGateway = cls.env["edi.gateway"]
        EdiTransfer = cls.env["edi.transfer"]
        EdiDocument = cls.env["edi.document"]

        # Create gateway
        cls.gateway = EdiGateway.create(
            {
                "name": "Test gateway",
                "model_id": IrModel._get_id("edi.connection.model"),
            }
        )

        # Create transfers
        cls.xfer_monday = EdiTransfer.create(
            {
                "gateway_id": cls.gateway.id,
            }
        )
        cls.xfer_tuesday = EdiTransfer.create(
            {
                "gateway_id": cls.gateway.id,
            }
        )

        # Create documents
        cls.doc_todo = EdiDocument.create(
            {
                "name": "ToDo list",
                "doc_type_id": cls.doc_type_unknown.id,
            }
        )
        cls.doc_doing = EdiDocument.create(
            {
                "name": "In progress list",
                "state": "done",
                "doc_type_id": cls.doc_type_unknown.id,
            }
        )
        cls.doc_done = EdiDocument.create(
            {
                "name": "Completed list",
                "state": "done",
                "doc_type_id": cls.doc_type_unknown.id,
            }
        )

    def assertActionDomains(self, xfer):
        """Assert that actions product the correct search domains"""
        EdiDocument = self.env["edi.document"]
        IrAttachment = self.env["ir.attachment"]

        # Check view documents
        view_docs = xfer.action_view_docs()
        self.assertEqual(EdiDocument.search(view_docs["domain"]), xfer.doc_ids)

        # Check view input attachments
        view_inputs = xfer.action_view_inputs()
        self.assertEqual(IrAttachment.search(view_inputs["domain"]), xfer.input_ids)

        # Check view output attachments
        view_outputs = xfer.action_view_outputs()
        self.assertEqual(IrAttachment.search(view_outputs["domain"]), xfer.output_ids)

    def test01_no_docs(self):
        """Test with no documents"""
        self.assertEqual(self.xfer_monday.doc_count, 0)
        self.assertEqual(self.xfer_monday.input_count, 0)
        self.assertEqual(self.xfer_monday.output_count, 0)
        self.assertActionDomains(self.xfer_monday)

    def test02_empty_doc(self):
        """Test with an empty document"""
        self.doc_todo.transfer_id = self.xfer_monday
        self.assertEqual(self.xfer_monday.doc_count, 1)
        self.assertEqual(self.xfer_monday.input_count, 0)
        self.assertEqual(self.xfer_monday.output_count, 0)
        self.assertActionDomains(self.xfer_monday)

    def test03_input_doc(self):
        """Test with a single-attachment input document"""
        self.create_input_attachment(self.doc_todo, "save_world.txt")
        self.xfer_monday.doc_ids += self.doc_todo
        self.xfer_monday.input_ids += self.doc_todo.input_ids
        self.xfer_monday.output_ids += self.doc_todo.output_ids
        self.assertEqual(self.xfer_monday.doc_count, 1)
        self.assertEqual(self.xfer_monday.input_count, 1)
        self.assertEqual(self.xfer_monday.output_count, 0)
        self.assertActionDomains(self.xfer_monday)

    def test04_output_doc(self):
        """Test with a single-attachment output document"""
        self.create_output_attachment(self.doc_todo, "save_world.txt")
        self.xfer_monday.doc_ids += self.doc_todo
        self.xfer_monday.input_ids += self.doc_todo.input_ids
        self.xfer_monday.output_ids += self.doc_todo.output_ids
        self.assertEqual(self.xfer_monday.doc_count, 1)
        self.assertEqual(self.xfer_monday.input_count, 0)
        self.assertEqual(self.xfer_monday.output_count, 1)
        self.assertActionDomains(self.xfer_monday)

    def test05_multi_doc(self):
        """Test with multiple document and attachments"""
        self.create_input_attachment(self.doc_done, "hello_world.txt")
        self.create_input_attachment(self.doc_done, "save_world.txt")
        self.create_output_attachment(self.doc_todo, "destroy_world.txt")
        self.xfer_monday.doc_ids += self.doc_done
        self.xfer_monday.input_ids += self.doc_done.input_ids
        self.xfer_monday.output_ids += self.doc_done.output_ids
        self.xfer_tuesday.doc_ids += self.doc_doing
        self.xfer_tuesday.input_ids += self.doc_doing.input_ids
        self.xfer_tuesday.output_ids += self.doc_doing.output_ids
        self.xfer_tuesday.doc_ids += self.doc_todo
        self.xfer_tuesday.input_ids += self.doc_todo.input_ids
        self.xfer_tuesday.output_ids += self.doc_todo.output_ids
        self.assertEqual(self.xfer_monday.doc_count, 1)
        self.assertEqual(self.xfer_monday.input_count, 2)
        self.assertEqual(self.xfer_monday.output_count, 0)
        self.assertActionDomains(self.xfer_monday)
        self.assertEqual(self.xfer_tuesday.doc_count, 2)
        self.assertEqual(self.xfer_tuesday.input_count, 0)
        self.assertEqual(self.xfer_tuesday.output_count, 1)
        self.assertActionDomains(self.xfer_tuesday)
