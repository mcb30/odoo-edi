"""EDI issue tests"""

from . import common
from odoo.exceptions import UserError, ValidationError


class TestEdiIssue(common.BaseEDI):
    """EDI issue tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        EdiDocument = cls.env['edi.document']

        cls.doc = EdiDocument.create({
            'name': "ToDo list (Today)",
            'doc_type_id': cls.document_type_unknown.id,
            'state': 'draft',
        })

    def _get_action_view_issues_test_fields(self, doc):
        domain = [(doc._fields['issue_ids'].inverse_name, '=', doc.id)]
        context = {
            'default_%s' % k: v for k, v in doc._issue_vals().items()
        }
        context.update({'create': True})

        return {
            'domain': domain,
            'context': context,
        }

    def test01_action_close_issues(self):
        issue = self.doc.raise_issue('Test issue: %s', UserError('Test close issues'))
        self.assertIn(issue, self.doc.issue_ids)
        # close document issues
        self.doc.action_close_issues()
        issues = self.doc.issue_ids
        self.assertEqual(len(issues), 0)

    def test02_action_view_issues(self):
        issue = self.doc.raise_issue('Test issue: %s', UserError('Test close issues'))
        self.assertIn(issue, self.doc.issue_ids)

        action = self._get_action_view_issues_test_fields(self.doc)
        res = self.doc.action_view_issues()
        self.assertIsSubset(action, res)

    def test03_raise_issue_non_usererror(self):
        issue = self.doc.raise_issue('Test issue: %s', ValidationError('Test non UserError issue'))
        self.assertIn(issue, self.doc.issue_ids)

