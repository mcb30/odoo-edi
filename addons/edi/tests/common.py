"""EDI tests"""

import base64
from datetime import datetime, timedelta
from odoo import fields
from odoo.tests import common

import fnmatch
import os.path
import time
from pathlib import Path



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


class BaseEDI(common.SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(BaseEDI, cls).setUpClass()
        cls.document_type_unknown = cls.env.ref('edi.document_type_unknown')

    @classmethod
    def tearDownClass(cls):
        super(BaseEDI, cls).tearDownClass()

    @classmethod
    def _create_local_gateway(cls):
        model_id = cls.env.ref('edi.model_edi_connection_local')
        return cls._create_gateway(name='Local Filesystem Test Gateway',
                                   model_id=model_id.id)

    @classmethod
    def _create_gateway(cls, **data):
        EdiGateway = cls.env['edi.gateway']

        return EdiGateway.create(data)

    @classmethod
    def _touch_files(cls, path):
        """ Touch all the files matching the edi.gateway.path """
        cls._touch_files_in_path(path.path, path.glob)

    @staticmethod
    def _touch_files_in_path(path, glob):
        for filename in os.listdir(path):
            # Skip files not matching pattern
            if not fnmatch.fnmatch(filename, glob):
                continue

            filepath = os.path.join(path, filename)
            Path(filepath).touch()

    @classmethod
    def _create_local_path(cls, gateway, touch_files=True, folder='files',
                           **kwargs):
        directory = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), folder
        )
        data = {
            'name': 'Local path for %s' % gateway.name,
            'gateway_id': gateway.id,
            'glob': '*.txt',
            'path': directory,
            'age_window': 24,
        }
        if kwargs:
            data.update(kwargs)
        path = cls._create_path(**data)

        if touch_files:
            cls._touch_files(path)

        return path

    @classmethod
    def _create_path(cls, **data):
        EdiPath = cls.env['edi.gateway.path']

        return EdiPath.create(data)

    @classmethod
    def _create_document(cls, document_type):
        """ Create a document of type document_type """
        EDIDocument = cls.env['edi.document']

        return EDIDocument.create({'doc_type_id': document_type.id})

    @classmethod
    def _create_attachment(cls, doc, file_text, file_name, attach_type='input'):
        """
            Create an attachment and related it to a document depending on the
            attachment type: input or output.
        """
        Attachment = cls.env['ir.attachment']

        if attach_type == 'output':
            res_field = 'output_ids'
        else:
            res_field = 'input_ids'

        attachment = Attachment.create({
            'name': file_name,
            'datas_fname': file_name,
            'datas': base64.b64encode(file_text.encode()),
            'res_model': 'edi.document',
            'res_field': res_field,
            'res_id': doc.id,
        })

        return attachment

    @staticmethod
    def _generate_file_name(prefix='test_', suffix='.txt'):
        return "{}{}{}".format(prefix, int(time.time()), suffix)

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

    def assertIsSubset(self, dict1, dict2):
        for key, value in dict1.items():
            self.assertEqual(value, dict2[key])
