"""EDI tests"""

import base64
from datetime import datetime
import os
import pathlib
from odoo.modules.module import get_resource_path
from odoo.tests import common


class EdiTestFile(os.PathLike):
    """An EDI test file

    A test file accessible via the ``self.files`` attribute of any EDI
    test case.  These are files present within the source tree that
    are available for use by unit tests.

    Functions that accept test files as parameters will generally
    accept either a plain string or an ``EdiTestFile`` object.  Use an
    ``EdiTestFile`` object when additional metadata (e.g. the required
    file age) must be provided.
    """

    def __init__(self, file, age=None):
        self.file = file
        self.age = age

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.file)

    def __str__(self):
        return self.file

    def __fspath__(self):
        return self.file

    @property
    def mtime(self):
        """File modification time"""
        now = datetime.now()
        return now if self.age is None else now - self.age


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
