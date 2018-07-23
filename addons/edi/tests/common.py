"""EDI tests"""

import base64
from contextlib import contextmanager
from datetime import datetime
import pathlib
import sys
from unittest.mock import patch
from odoo.exceptions import UserError
from odoo.modules.module import get_resource_from_path, get_resource_path
from odoo.tools import mute_logger
from odoo.tests import common


class EdiTestFile(pathlib.PurePosixPath):
    """An EDI test file

    A test file accessible via the ``self.files`` attribute of any EDI
    test case.  These are files present within the source tree that
    are available for use by unit tests.

    Functions that accept test files as parameters will generally
    accept either a plain string or an ``EdiTestFile`` object.  Use an
    ``EdiTestFile`` object when additional metadata (e.g. the required
    file age) must be provided.
    """

    def __new__(cls, *args, age=None, **kwargs):
        # pylint: disable=arguments-differ
        path = super().__new__(cls, *args, **kwargs)
        path.age = age
        return path

    @property
    def mtime(self):
        """File modification time"""
        now = datetime.now()
        return now if self.age is None else now - self.age


@common.at_install(False)
@common.post_install(True)
class EdiCase(common.SavepointCase):
    """Base test case for EDI models"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc_type_unknown = cls.env.ref('edi.document_type_unknown')

        # Locate test file directory corresponding to the class (which
        # may be a derived class in a different module).
        module_file = sys.modules[cls.__module__].__file__
        module = get_resource_from_path(module_file)[0]
        cls.files = pathlib.Path(get_resource_path(module, 'tests', 'files'))

        # Delete any document types corresponding to non-existent
        # models, to avoid failures in edi.document.type.autocreate()
        EdiDocumentType = cls.env['edi.document.type']
        EdiDocumentType.search([]).filtered(
            lambda x: x.model_id.model not in cls.env
        ).unlink()

    @classmethod
    def create_attachment(cls, *filenames):
        """Create attachment(s)"""
        IrAttachment = cls.env['ir.attachment']
        attachments = IrAttachment.browse()
        for filename in filenames:
            path = cls.files.joinpath(filename)
            attachments += IrAttachment.create({
                'name': path.name,
                'datas_fname': path.name,
                'datas': base64.b64encode(path.read_bytes()),
            })
        return attachments

    @classmethod
    def create_input_attachment(cls, doc, *filenames):
        """Create input attachment(s)"""
        attachments = cls.create_attachment(*filenames)
        attachments.write({
            'res_model': 'edi.document',
            'res_field': 'input_ids',
            'res_id': doc.id,
        })
        return attachments

    @classmethod
    def create_input_document(cls, doc_type, *filenames):
        """Create input document with attachment(s)"""
        EdiDocument = cls.env['edi.document']
        doc = EdiDocument.create({
            'name': "Test %s" % doc_type.name,
            'doc_type_id': doc_type.id,
        })
        cls.create_input_attachment(doc, *filenames)
        return doc

    @classmethod
    def create_output_attachment(cls, doc, *filenames):
        """Create output attachment(s)"""
        attachments = cls.create_attachment(*filenames)
        attachments.write({
            'res_model': 'edi.document',
            'res_field': 'output_ids',
            'res_id': doc.id,
        })
        return attachments

    def assertAttachment(self, attachment, filename=None):
        """Assert that attachment content is as expected"""
        if filename is None:
            filename = attachment.datas_fname
        data = self.files.joinpath(filename).read_bytes()
        self.assertEqual(attachment.datas_fname, filename)
        self.assertEqual(base64.b64decode(attachment.datas), data)

    @contextmanager
    def assertRaisesIssue(self, entity, exception=UserError):
        """Assert that an issue is raised on the specified entity"""
        EdiIssues = self.env['edi.issues']
        old_issue_ids = entity.issue_ids
        mute = ['odoo.addons.edi.models.edi_issues']
        with mute_logger(*mute), patch.object(
            EdiIssues.__class__, 'raise_issue', autospec=True,
            side_effect=EdiIssues.__class__.raise_issue
        ) as mock_raise_issue:
            yield
        new_issue_ids = entity.issue_ids - old_issue_ids

        # Fail if no issue was ever raised
        self.assertTrue(mock_raise_issue.called)

        # Retrieve all exceptions passed to raise_issue(), and
        # identify the one that we wish to blame for any test
        # failures.  If any unexpected exceptions occurred then we
        # blame the first of those; otherwise we arbitrarily blame the
        # first exception.  This is something of a heuristic, but
        # should handle most cases correctly.
        errors = [err for ((_self, _fmt, err), _kwargs) in
                  mock_raise_issue.call_args_list]
        scapegoat = sorted(errors, key=lambda x: isinstance(x, exception))[0]

        # Fail if more than one issue was raised, or if an unexpected
        # issue was raised.
        try:
            self.assertEqual(len(new_issue_ids), 1)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], exception)
        except AssertionError as assertion:
            raise assertion from scapegoat

        # Delete the raised issue
        new_issue_ids.unlink()
