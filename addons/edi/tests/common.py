"""EDI tests"""

import base64
from datetime import datetime, timedelta
from odoo import fields
from odoo.tests import common


class EdiConnectionCase(common.SavepointCase):
    """Base test case for EDI connection models"""

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
        today = fields.Datetime.now()
        yesterday = fields.Datetime.to_string(datetime.now() -
                                              timedelta(hours=36))
        cls.doc_today = EdiDocument.create({
            'name': "ToDo list (Today)",
            'doc_type_id': cls.doc_type.id,
            'state': 'done',
            'prepare_date': today,
            'execute_date': today,
        })
        cls.doc_yesterday = EdiDocument.create({
            'name': "ToDo list (Yesterday)",
            'doc_type_id': cls.doc_type.id,
            'state': 'done',
            'prepare_date': yesterday,
            'execute_date': yesterday,
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

    def attach_inputs(self, doc, attachments):
        """Add input attachments to EDI document"""
        attachments.write({
            'res_model': 'edi.document',
            'res_field': 'input_ids',
            'res_id': doc.id,
        })
        for attachment in attachments:
            self.assertIn(attachment, doc.input_ids)

    def attach_outputs(self, doc, attachments):
        """Add output attachments to EDI document"""
        attachments.write({
            'res_model': 'edi.document',
            'res_field': 'output_ids',
            'res_id': doc.id,
        })
        for attachment in attachments:
            self.assertIn(attachment, doc.output_ids)
