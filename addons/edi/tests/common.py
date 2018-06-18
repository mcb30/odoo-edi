"""EDI tests"""

import base64
import pathlib
from odoo.modules.module import get_resource_path
from odoo.tests import common


class EdiCase(common.SavepointCase):
    """Base test case for EDI models"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc_type_unknown = cls.env.ref('edi.document_type_unknown')
        cls.files = pathlib.Path(get_resource_path('edi', 'tests', 'files'))

    @classmethod
    def create_attachment(cls, filename):
        """Create attachment"""
        IrAttachment = cls.env['ir.attachment']
        path = cls.files.joinpath(filename)
        return IrAttachment.create({
            'name': path.name,
            'datas_fname': path.name,
            'datas': base64.b64encode(path.read_bytes()),
        })

    @classmethod
    def create_input_attachment(cls, doc, filename):
        """Create input attachment"""
        attachment = cls.create_attachment(filename)
        attachment.write({
            'res_model': 'edi.document',
            'res_field': 'input_ids',
            'res_id': doc.id,
        })
        return attachment

    @classmethod
    def create_output_attachment(cls, doc, filename):
        """Create output attachment"""
        attachment = cls.create_attachment(filename)
        attachment.write({
            'res_model': 'edi.document',
            'res_field': 'output_ids',
            'res_id': doc.id,
        })
        return attachment

    def assertAttachment(self, attachment, filename=None):
        """Assert that attachment content is as expected"""
        if filename is None:
            filename = attachment.datas_fname
        data = self.files.joinpath(filename).read_bytes()
        self.assertEqual(attachment.datas_fname, filename)
        self.assertEqual(base64.b64decode(attachment.datas), data)
