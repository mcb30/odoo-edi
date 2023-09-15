"""EDI partner tests"""

from .common import EdiCase


class TestPartner(EdiCase):
    """EDI partner tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        EdiDocumentType = cls.env["edi.document.type"]
        IrModel = cls.env["ir.model"]

        cls.rec_type_partner = cls.env.ref("edi.partner_record_type")

        cls.doc_type_partner = EdiDocumentType.create(
            {
                "name": "Dummy partner document",
                "model_id": IrModel._get_id("edi.partner.document"),
                "rec_type_ids": [(6, 0, [cls.rec_type_partner.id])],
            }
        )
        cls.rec_type_partner_title = cls.env.ref("edi.partner_title_record_type")

        cls.doc_type_partner_title = EdiDocumentType.create(
            {
                "name": "Dummy partner title document",
                "model_id": IrModel._get_id("edi.partner.title.document"),
                "rec_type_ids": [(6, 0, [cls.rec_type_partner_title.id])],
            }
        )

    def test_partner(self):
        """Test partner document with dummy input attachment"""
        EdiDocument = self.env["edi.document"]
        doc = EdiDocument.create(
            {
                "name": "Dummy partner test",
                "doc_type_id": self.doc_type_partner.id,
            }
        )
        self.create_input_attachment(doc, "dummy.txt")
        doc.action_execute()

    def test_partner_title(self):
        """Test partner title document with dummy input attachment"""
        EdiDocument = self.env["edi.document"]
        EdiPartnerTitleRecord = self.env["edi.partner.title.record"]
        doc = EdiDocument.create(
            {
                "name": "Dummy partner title test",
                "doc_type_id": self.doc_type_partner_title.id,
            }
        )
        self.create_input_attachment(doc, "dummy.txt")
        self.assertTrue(doc.action_prepare())
        # There is no tutorial model for partner titles, so create a
        # record manually to exercise all code paths.
        EdiPartnerTitleRecord.create(
            {
                "doc_id": doc.id,
                "name": "Lieutenant",
                "shortcut": "Lt.",
            }
        )
        self.assertTrue(doc.action_execute())
        titles = doc.mapped("partner_title_ids.title_id")
        self.assertEqual(len(titles), 1)
        self.assertEqual(titles.name, "Lieutenant")
        self.assertEqual(titles.shortcut, "Lt.")
