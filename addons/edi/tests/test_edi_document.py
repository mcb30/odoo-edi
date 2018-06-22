"""EDI document tests"""

from odoo.exceptions import UserError
from . import common


class TestEdiDocument(common.EdiCase):
    """EDI document tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        EdiDocumentType = cls.env['edi.document.type']
        EdiDocument = cls.env['edi.document']
        IrModel = cls.env['ir.model']
        # Create document types
        cls.doc_type = EdiDocumentType.create({
            'name': "Test EDI document",
            'model_id': IrModel._get_id('edi.document.model'),
        })

        cls.doc = EdiDocument.create({
            'name': "ToDo list",
            'doc_type_id': cls.doc_type.id,
            'state': 'draft',
        })

    def test01_prepare_document(self):
        """ Test action prepare"""
        res = self.doc.action_prepare()
        self.assertTrue(res)

    def test02_prepare_unknown_document(self):
        """ Test action prepare unknown document"""
        self.doc.doc_type_id = self.doc_type_unknown
        with self.assertRaisesIssue(self.doc):
            self.doc.action_prepare()

    def test03_unprepare_document(self):
        """ Test action unprepare"""
        res = self.doc.action_prepare()
        self.assertTrue(res)
        res = self.doc.action_unprepare()
        self.assertTrue(res)

    def test04_execute_document(self):
        """ Test action execute"""
        res = self.doc.action_execute()
        self.assertTrue(res)

    def test05_unprepare_executed_document(self):
        """ Test action unprepare of an executed document"""
        res = self.doc.action_execute()
        self.assertTrue(res)
        with self.assertRaises(UserError):
            self.doc.action_unprepare()

    def test06_execute_executed_document(self):
        """ Test action execute of an executed document"""
        res = self.doc.action_execute()
        self.assertTrue(res)
        with self.assertRaises(UserError):
            self.doc.action_execute()

    def test07_cancel_prepared_document(self):
        """ Test action cancel of a prepared document"""

        res = self.doc.action_prepare()
        self.assertTrue(res)
        res = self.doc.action_cancel()
        self.assertTrue(res)

    def test08_cancel_executed_document(self):
        """ Test action cancel of an executed document"""
        res = self.doc.action_execute()
        self.assertTrue(res)
        with self.assertRaises(UserError):
            self.doc.action_cancel()

    def test09_prepare_executed_document(self):
        """ Test action prepare of an executed document"""
        res = self.doc.action_execute()
        self.assertTrue(res)
        with self.assertRaises(UserError):
            self.doc.action_prepare()

    def test10_action_view_inputs(self):
        """ Test action view inputs"""
        Attachment = self.env['ir.attachment']
        action = self.doc.action_view_inputs()
        self.assertEqual(len(Attachment.search(action['domain'])), 0)
        attachment = Attachment.with_context(action['context']).create({
            'name': "Test context input attachments",
        })
        self.assertIn(attachment, self.doc.input_ids)
        self.assertEqual(len(Attachment.search(action['domain'])), 1)

    def test11_action_view_outputs(self):
        """ Test action view outputs"""
        Attachment = self.env['ir.attachment']
        action = self.doc.action_view_outputs()
        self.assertEqual(len(Attachment.search(action['domain'])), 0)
        attachment = Attachment.with_context(action['context']).create({
            'name': "Test context output attachments",
        })
        self.assertIn(attachment, self.doc.output_ids)
        self.assertEqual(len(Attachment.search(action['domain'])), 1)

    def test12_copy_document_one_attachment(self):
        """ Test copy a document with one input attachment"""
        save = self.create_input_attachment(self.doc, "save_world.txt")
        self.assertIn(save, self.doc.input_ids)
        doc2 = self.doc.copy()
        self.assertEqual(len(doc2.input_ids), 1)
        self.assertAttachment(doc2.input_ids[0], "save_world.txt")

    def test13_copy_document_two_attachments(self):
        """ Test copy a document with two input attachments"""
        save = self.create_input_attachment(self.doc, "save_world.txt")
        destroy = self.create_input_attachment(self.doc, "destroy_world.txt")
        self.assertIn(save, self.doc.input_ids)
        self.assertIn(destroy, self.doc.input_ids)
        doc2 = self.doc.copy()
        self.assertEqual(len(doc2.input_ids), 2)
        for attachment in doc2.input_ids:
            self.assertAttachment(attachment)
