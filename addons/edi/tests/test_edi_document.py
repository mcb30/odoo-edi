"""EDI document tests"""

import base64
from odoo import fields, _

from odoo.exceptions import UserError

from . import common


class TestEdiDocument(common.BaseEDI):
    """EDI document tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        EdiDocumentType = cls.env['edi.document.type']
        EdiDocument = cls.env['edi.document']
        IrModel = cls.env['ir.model']
        IrAttachment = cls.env['ir.attachment']
        # Create document types
        cls.doc_type = EdiDocumentType.create({
            'name': "Test EDI document",
            'model_id': IrModel._get_id('edi.document.model'),
        })
        # Create documents
        # today = fields.Datetime.now()

        cls.doc = EdiDocument.create({
            'name': "ToDo list (Today)",
            'doc_type_id': cls.doc_type.id,
            'state': 'draft',
        })

        # Create attachments
        cls.att_save_world = IrAttachment.create({
            'name': "save_world.txt",
            'datas_fname': "save_world.txt",
            'datas': base64.b64encode("Save the world".encode()),
        })
        cls.att_destroy_world = IrAttachment.create({
            'name': "destroy_world.txt",
            'datas_fname': "destroy_world.txt",
            'datas': base64.b64encode("Destroy the world".encode()),
        })
        cls.att_both = cls.att_save_world | cls.att_destroy_world

    def _get_action_view_attachments_test_fields(self, doc, res_field):
        self.assertIn(res_field, ['input_ids', 'output_ids'])
        name = "Inputs" if res_field == 'input_ids'else "Outputs"
        return {
            'display_name': _(name),
            'domain': [('res_model', '=', 'edi.document'),
                       ('res_field', '=', res_field),
                       ('res_id', '=', doc.id)],
            'context': {'default_res_model': 'edi.document',
                        'default_res_field': res_field,
                        'default_res_id': doc.id}
        }

    def test01_prepare_document(self):
        res = self.doc.action_prepare()
        self.assertTrue(res)

    def test02_unprepare_document(self):
        res = self.doc.action_prepare()
        self.assertTrue(res)
        res = self.doc.action_unprepare()
        self.assertTrue(res)

    def test03_execute_document(self):
        res = self.doc.action_execute()
        self.assertTrue(res)

    def test04_unprepare_executed_document(self):
        res = self.doc.action_execute()
        self.assertTrue(res)
        with self.assertRaises(UserError) as e:
            self.doc.action_unprepare()

        self.assertEqual(e.exception.name,
                         'Cannot unprepare a %s document' %
                         self.doc._get_state_name())

    def test05_execute_executed_document(self):
        res = self.doc.action_execute()
        self.assertTrue(res)
        with self.assertRaises(UserError) as e:
            self.doc.action_execute()

        self.assertEqual(e.exception.name,
                         'Cannot execute a %s document' %
                         self.doc._get_state_name())

    def test06_cancel_prepared_document(self):
        res = self.doc.action_prepare()
        self.assertTrue(res)
        res = self.doc.action_cancel()
        self.assertTrue(res)

    def test07_cancel_executed_document(self):
        res = self.doc.action_execute()
        self.assertTrue(res)
        with self.assertRaises(UserError) as e:
            self.doc.action_cancel()
        self.assertEqual(e.exception.name,
                         'Cannot cancel a %s document' %
                         self.doc._get_state_name())

    def test08_prepare_executed_document(self):
        res = self.doc.action_execute()
        self.assertTrue(res)
        with self.assertRaises(UserError) as e:
            self.doc.action_prepare()
        self.assertEqual(e.exception.name,
                         'Cannot prepare a %s document' %
                         self.doc._get_state_name())

    def test09_action_view_inputs(self):
        action = self._get_action_view_attachments_test_fields(self.doc, 'input_ids')
        res = self.doc.action_view_inputs()
        for key, value in action.items():
            self.assertEqual(value, res[key])

    def test10_action_view_outputs(self):
        action = self._get_action_view_attachments_test_fields(self.doc, 'output_ids')
        res = self.doc.action_view_outputs()
        self.assertIsSubset(action, res)

    def test11_copy_document_one_attachment(self):
        self.attach_inputs(self.doc, self.att_save_world)
        doc2 = self.doc.copy()
        self.assertEqual(len(doc2.input_ids), 1)
        self.assertEqual(doc2.input_ids[0].datas, self.doc.input_ids[0].datas)

    def test12_copy_document_two_attachments(self):
        self.attach_inputs(self.doc, self.att_both)
        doc2 = self.doc.copy()
        self.assertEqual(len(doc2.input_ids), 2)
        for att in doc2.input_ids:
            self.assertIn(att.name, self.doc.mapped('input_ids.name'))

