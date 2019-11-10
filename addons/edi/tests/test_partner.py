"""EDI partner tests"""

from .common import EdiCase
from unittest.mock import patch
from odoo.tools import mute_logger


class TestPartner(EdiCase):
    """EDI partner tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        EdiRecordType = cls.env['edi.record.type']
        EdiDocumentType = cls.env['edi.document.type']
        IrModel = cls.env['ir.model']
        cls.rec_type_partner = EdiRecordType.create({
            'name': "Dummy partner record",
            'model_id': IrModel._get_id('edi.partner.record'),
        })
        cls.doc_type_partner = EdiDocumentType.create({
            'name': "Dummy partner document",
            'model_id': IrModel._get_id('edi.partner.document'),
            'rec_type_ids': [(6, 0, [cls.rec_type_partner.id])],
        })
        cls.rec_type_partner_title = EdiRecordType.create({
            'name': "Dummy partner title record",
            'model_id': IrModel._get_id('edi.partner.title.record'),
        })
        cls.doc_type_partner_title = EdiDocumentType.create({
            'name': "Dummy partner title document",
            'model_id': IrModel._get_id('edi.partner.title.document'),
            'rec_type_ids': [(6, 0, [cls.rec_type_partner_title.id])],
        })

    def test01_partner(self):
        """Test partner document with dummy input attachment"""
        EdiDocument = self.env['edi.document']
        doc = EdiDocument.create({
            'name': "Dummy partner test",
            'doc_type_id': self.doc_type_partner.id,
        })
        self.create_input_attachment(doc, 'dummy.txt')
        doc.action_execute()

    def test02_partner_title(self):
        """Test partner title document with dummy input attachment"""
        EdiDocument = self.env['edi.document']
        EdiPartnerTitleRecord = self.env['edi.partner.title.record']
        doc = EdiDocument.create({
            'name': "Dummy partner title test",
            'doc_type_id': self.doc_type_partner_title.id,
        })
        self.create_input_attachment(doc, 'dummy.txt')
        self.assertTrue(doc.action_prepare())
        # There is no tutorial model for partner titles, so create a
        # record manually to exercise all code paths.
        EdiPartnerTitleRecord.create({
            'doc_id': doc.id,
            'name': "Lieutenant",
            'shortcut': "Lt.",
        })
        self.assertTrue(doc.action_execute())
        titles = doc.mapped('partner_title_ids.title_id')
        self.assertEqual(len(titles), 1)
        self.assertEqual(titles.name, "Lieutenant")
        self.assertEqual(titles.shortcut, "Lt.")

    def test03_partner_rollback(self):
        """Test partner title document with a failure - ensure that the rollback
         happens and the cache is properly cleared after a rollback
         """
        EdiDocument = self.env['edi.document']
        EdiPartnerRecord = self.env['edi.partner.record']
        Partner = self.env['res.partner']
        # Create a partner that will be updated by an EDI record
        test_partner = Partner.create({'name': 'Joe', 'ref': 'test_partner'})
        # Create an EDI document
        doc = EdiDocument.create({
            'name': "Partner rollback test",
            'doc_type_id': self.doc_type_partner.id,
        })
        # Create an edi partner record to modify the test partner's name
        EdiPartnerRecord.create({
            'doc_id': doc.id,
            'name': "test_partner",
            'full_name': "Dave",
        })
        # Use dummy input and prepare document
        self.create_input_attachment(doc, 'dummy.txt')
        self.assertTrue(doc.action_prepare())
        # Patch execute to force a failure
        DocModel = self.env[doc.doc_type_id.model_id.model]

        def patched_execute(EdiDocumentModel):
            EdiDocumentModel.execute_records()
            raise ValueError()
        patched_class = patch.object(
            DocModel.__class__,
            'execute',
            side_effect=patched_execute
        )
        # Assert that document fails to execute with patch
        with patched_class, mute_logger('odoo.addons.edi.models.edi_issues'):
            self.assertFalse(doc.action_execute())
        # After an execution failure, the test partner should still be Joe
        self.assertEqual(test_partner.name, 'Joe')
