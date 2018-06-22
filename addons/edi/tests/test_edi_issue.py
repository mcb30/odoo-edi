"""EDI issue tests"""

from odoo.exceptions import UserError, ValidationError
from .common import EdiCase


class TestEdiIssue(EdiCase):
    """EDI issue tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        EdiDocument = cls.env['edi.document']

        # Create document
        cls.doc = EdiDocument.create({
            'name': "ToDo list",
            'doc_type_id': cls.doc_type_unknown.id,
            'state': 'draft',
        })

    def test01_action_close_issues(self):
        """Test action close issues"""
        issue = self.doc.raise_issue("Test issue: %s",
                                     UserError("Test close issues"))
        self.assertIn(issue, self.doc.issue_ids)
        self.doc.action_close_issues()
        self.assertEqual(len(self.doc.issue_ids), 0)

    def test02_action_view_issues(self):
        """Test action view issues"""
        ProjectTask = self.env['project.task']
        action = self.doc.action_view_issues()
        self.assertEqual(len(ProjectTask.search(action['domain'])), 0)
        issue = ProjectTask.with_context(action['context']).create({
            'name': "Test context issue",
        })
        self.assertIn(issue, self.doc.issue_ids)
        self.assertEqual(len(ProjectTask.search(action['domain'])), 1)

    def test03_raise_issue_non_usererror(self):
        """Test issue raised non UserError"""
        issue = self.doc.raise_issue("Test issue: %s",
                                     ValidationError("Test non UserError"))
        self.assertIn(issue, self.doc.issue_ids)
