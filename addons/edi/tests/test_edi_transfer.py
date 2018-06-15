"""EDI transfer tests"""

from odoo import fields, _
from unittest.mock import patch

from . import common


class TestEdiTransfer(common.BaseEDI):
    """EDI transfer tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        EdiDocumentType = cls.env['edi.document.type']
        EdiDocument = cls.env['edi.document']
        EdiTransfer = cls.env['edi.transfer']
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

        cls.gw = cls._create_local_gateway()
        cls.transfer = EdiTransfer.create({'gateway_id': cls.gw.id})

    def _get_action_view_attachments_test_fields(self, transfer, res_field):
        self.assertIn(res_field, ['input_ids', 'output_ids'])
        name = "Inputs" if res_field == 'input_ids'else "Outputs"
        return {
            'display_name': _(name),
            'domain':  [('id', 'in', transfer.mapped('{}.id'.format(res_field)))],
            'context': {'create': False}
        }

    def _get_action_view_docs_test_fields(self, transfer):
        return {
            'domain':  [('transfer_id', '=', transfer.id)],
            'context': {'create': False}
        }

    def test01_action_view_inputs(self):
        action = self._get_action_view_attachments_test_fields(self.transfer, 'input_ids')
        res = self.transfer.action_view_inputs()
        for key, value in action.items():
            self.assertEqual(value, res[key])

    def test02_action_view_outputs(self):
        action = self._get_action_view_attachments_test_fields(self.transfer, 'output_ids')
        res = self.transfer.action_view_outputs()
        self.assertIsSubset(action, res)

    def test03_action_view_documents(self):
        action = self._get_action_view_docs_test_fields(self.transfer)
        res = self.transfer.action_view_docs()
        self.assertIsSubset(action, res)

    def test04_do_transfer(self):
        self.doc.transfer_id = self.transfer

        self.assertTrue(self.transfer.allow_process)
        self._create_local_path(gateway=self.gw,
                                allow_send=False,
                                doc_type_ids=[(6, 0, [self.doc_type.id])]
                                )
        transfer = self.gw.do_transfer()

    def test05_do_transfer_only_prepare(self):
        self.doc.transfer_id = self.transfer

        self.assertTrue(self.transfer.allow_process)
        self._create_local_path(gateway=self.gw,
                                allow_send=False,
                                doc_type_ids=[(6, 0, [self.doc_type.id])]
                                )

        # Mock
        patcher = patch.object(self.doc.__class__, 'action_execute', autospec=True, return_value=False)
        self.patched_send = patcher.start()
        self.addCleanup(patcher.stop)

        transfer = self.gw.do_transfer()
        doc = transfer.doc_ids
        self.assertEqual(doc.state, 'prep')
