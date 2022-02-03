"""EDI document tests"""

from odoo.exceptions import UserError
from .common import EdiCase


class TestEdiDocument(EdiCase):
    """EDI document tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        EdiDocumentType = cls.env["edi.document.type"]
        EdiDocument = cls.env["edi.document"]
        IrModel = cls.env["ir.model"]

        # Create document type
        cls.doc_type = EdiDocumentType.create(
            {
                "name": "Test EDI document",
                "model_id": IrModel._get_id("edi.document.model"),
            }
        )

        # Create document
        cls.doc = EdiDocument.create(
            {
                "name": "ToDo list",
                "doc_type_id": cls.doc_type.id,
                "state": "draft",
            }
        )

    def test_prepare_document(self):
        """Test action prepare"""
        self.assertTrue(self.doc.action_prepare())

    def test_prepare_unknown_document(self):
        """Test action prepare unknown document"""
        self.doc.doc_type_id = self.doc_type_unknown
        with self.assertRaisesIssue(self.doc):
            self.doc.action_prepare()

    def test_unprepare_document(self):
        """Test action unprepare"""
        self.assertTrue(self.doc.action_prepare())
        self.assertTrue(self.doc.action_unprepare())

    def test_execute_document(self):
        """Test action execute"""
        self.assertTrue(self.doc.action_execute())

    def test_unprepare_executed_document(self):
        """Test action unprepare of an executed document"""
        self.assertTrue(self.doc.action_execute())
        with self.assertRaises(UserError):
            self.doc.action_unprepare()

    def test_execute_executed_document(self):
        """Test action execute of an executed document"""
        self.assertTrue(self.doc.action_execute())
        with self.assertRaises(UserError):
            self.doc.action_execute()

    def test_cancel_prepared_document(self):
        """Test action cancel of a prepared document"""
        self.assertTrue(self.doc.action_prepare())
        self.assertTrue(self.doc.action_cancel())

    def test_cancel_executed_document(self):
        """Test action cancel of an executed document"""
        self.assertTrue(self.doc.action_execute())
        with self.assertRaises(UserError):
            self.doc.action_cancel()

    def test_prepare_executed_document(self):
        """Test action prepare of an executed document"""
        self.assertTrue(self.doc.action_execute())
        with self.assertRaises(UserError):
            self.doc.action_prepare()

    def test_action_view_inputs(self):
        """Test action view inputs"""
        Attachment = self.env["ir.attachment"]
        action = self.doc.action_view_inputs()
        self.assertEqual(len(Attachment.search(action["domain"])), 0)
        attachment = Attachment.with_context(action["context"]).create(
            {
                "name": "Test context input attachments",
            }
        )
        self.assertIn(attachment, self.doc.input_ids)
        self.assertEqual(len(Attachment.search(action["domain"])), 1)

    def test_action_view_outputs(self):
        """Test action view outputs"""
        Attachment = self.env["ir.attachment"]
        action = self.doc.action_view_outputs()
        self.assertEqual(len(Attachment.search(action["domain"])), 0)
        attachment = Attachment.with_context(action["context"]).create(
            {
                "name": "Test context output attachments",
            }
        )
        self.assertIn(attachment, self.doc.output_ids)
        self.assertEqual(len(Attachment.search(action["domain"])), 1)

    def test_copy_document_one_attachment(self):
        """Test copy a document with one input attachment"""
        save = self.create_input_attachment(self.doc, "save_world.txt")
        self.assertIn(save, self.doc.input_ids)
        doc2 = self.doc.copy()
        self.assertEqual(len(doc2.input_ids), 1)
        self.assertAttachment(doc2.input_ids[0], "save_world.txt")

    def test_copy_document_two_attachments(self):
        """Test copy a document with two input attachments"""
        save = self.create_input_attachment(self.doc, "save_world.txt")
        destroy = self.create_input_attachment(self.doc, "destroy_world.txt")
        self.assertIn(save, self.doc.input_ids)
        self.assertIn(destroy, self.doc.input_ids)
        doc2 = self.doc.copy()
        self.assertEqual(len(doc2.input_ids), 2)
        for attachment in doc2.input_ids:
            self.assertAttachment(attachment)
