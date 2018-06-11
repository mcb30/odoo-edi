import base64
import fnmatch
import os.path
import time
from pathlib import Path

from odoo.tests import common


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

    @staticmethod
    def _touch_files(path):
        """ Touch all the files matching the edi.gateway.path """
        for filename in os.listdir(path.path):
            # Skip files not matching pattern
            if not fnmatch.fnmatch(filename, path.glob):
                continue

            filepath = os.path.join(path.path, filename)
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
