"""EDI partner tutorial tests"""

from unittest import mock

from odoo import tools
from odoo.exceptions import ValidationError

from .common import EdiCase


class TestPartnerTutorial(EdiCase):
    """EDI partner tutorial tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc_type_tutorial = cls.env.ref(
            'edi.partner_tutorial_document_type'
        )

    @classmethod
    def create_tutorial(cls, *filenames, fail_fast=True):
        """Create partner tutorial document"""
        cls.doc_type_tutorial.fail_fast = fail_fast
        return cls.create_input_document(cls.doc_type_tutorial, *filenames)

    def test01_basic(self):
        """Basic document execution"""
        doc = self.create_tutorial('friends.csv')
        self.assertTrue(doc.action_execute())
        partners = doc.mapped('partner_tutorial_ids.partner_id')
        self.assertEqual(len(partners), 4)
        partners_by_ref = {x.ref: x for x in partners}
        self.assertEqual(partners_by_ref['A'].name, 'Alice')
        self.assertEqual(partners_by_ref['B'].email, 'bob@example.com')
        self.assertEqual(partners_by_ref['E'].title.name, 'Ms')
        self.assertFalse(partners_by_ref['U'].title)

    def test02_identical(self):
        """Document and subsequent identical document"""
        doc1 = self.create_tutorial('friends.csv')
        self.assertTrue(doc1.action_execute())
        self.assertEqual(len(doc1.partner_tutorial_ids), 4)
        doc2 = self.create_tutorial('friends.csv')
        self.assertTrue(doc2.action_execute())
        self.assertEqual(len(doc2.partner_tutorial_ids), 0)

    def test03_correction(self):
        """Document and subsequent correction document"""
        doc1 = self.create_tutorial('friends.csv')
        self.assertTrue(doc1.action_execute())
        partners = doc1.mapped('partner_tutorial_ids.partner_id')
        self.assertEqual(len(partners), 4)
        partners.filtered(lambda x: x.ref == 'E').email = 'eve@example.org'
        doc2 = self.create_tutorial('friends.csv')
        self.assertTrue(doc2.action_execute())
        partners = doc2.mapped('partner_tutorial_ids.partner_id')
        self.assertEqual(len(partners), 1)
        self.assertEqual(partners.ref, 'E')
        self.assertEqual(partners.email, 'eve@example.com')

    def test04_handles_correction_of_title(self):
        """Document and subsequent correction document"""
        Title = self.env['res.partner.title']
        doc1 = self.create_tutorial('friends.csv')
        self.assertTrue(doc1.action_execute())
        partners = doc1.mapped('partner_tutorial_ids.partner_id')
        self.assertEqual(len(partners), 4)
        doc2 = self.create_tutorial('update_untitled.csv')
        self.assertTrue(doc2.action_prepare())
        dame_title = Title.create({'name': 'Dame', 'shortcut': 'Dm'})
        self.assertTrue(doc2.action_execute())
        partners = doc2.mapped('partner_tutorial_ids.partner_id')
        self.assertEqual(len(partners), 1)
        self.assertEqual(partners.ref, 'U')
        self.assertEqual(partners.email, 'untitled@example.com')
        self.assertEqual(partners.title, dame_title)

    def test05_doppelganger(self):
        """Test that if a partner is repeated it is correctly ingested"""
        doc = self.create_tutorial('repeated_friend.csv')
        self.assertTrue(doc.action_execute())
        partners = doc.mapped('partner_tutorial_ids.partner_id')
        self.assertEqual(len(partners), 4)
        partners_by_ref = {x.ref: x for x in partners}
        self.assertEqual(partners_by_ref['A'].name, 'Alice')
        self.assertEqual(partners_by_ref['B'].email, 'bob@example.com')
        self.assertEqual(partners_by_ref['E'].title.name, 'Ms')
        self.assertFalse(partners_by_ref['U'].title)

    def test06_does_not_apply_invalid_update_if_failfast_is_off(self):
        """If fail fast is off, invalid updates should not be applied to their targets"""
        Partner = self.env['res.partner']
        doc1 = self.create_tutorial('friends.csv')
        self.assertTrue(doc1.action_execute())
        partners = doc1.mapped('partner_tutorial_ids.partner_id')
        self.assertEqual(len(partners), 4)
        partners_by_ref = {x.ref: x for x in partners}
        self.assertFalse(partners_by_ref['U'].title)
        doc2 = self.create_tutorial('update_untitled.csv', fail_fast=False)
        self.assertTrue(doc2.action_prepare())
        with mock.patch.object(Partner.__class__, 'write', create=True,
                               autospec=True,
                               side_effect=ValidationError('Test Error')):
            with tools.mute_logger('odoo.addons.edi.models.edi_synchronizer'):
                self.assertTrue(doc2.action_execute())
        partners = doc2.mapped('partner_tutorial_ids.partner_id')
        self.assertEqual(len(partners), 1)
        self.assertEqual(partners.ref, 'U')
        self.assertEqual(partners.email, 'untitled@example.com')
        self.assertFalse(partners.title)

    def test07_does_not_create_invalid_partners_if_failfast_is_off(self):
        """If fail fast is off, we create only valid customers"""
        Partner = self.env['res.partner']
        create_method = Partner.create

        def create_partner(*args, **kw):
            cls, vals = args
            if vals['name'] == 'Untitled':
                return ValidationError('Test Error')
            return create_method(vals)

        doc = self.create_tutorial('friends.csv', fail_fast=False)
        with mock.patch.object(Partner.__class__, 'create', create=True, autospec=True, side_effect=create_partner):
            self.assertTrue(doc.action_execute())
        partners = doc.mapped('partner_tutorial_ids.partner_id')
        self.assertEqual(len(partners), 3)
        partners_by_ref = {x.ref: x for x in partners}
        self.assertEqual(partners_by_ref['A'].name, 'Alice')
        self.assertEqual(partners_by_ref['B'].email, 'bob@example.com')
        self.assertEqual(partners_by_ref['E'].title.name, 'Ms')
