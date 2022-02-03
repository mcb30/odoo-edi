"""EDI product tests"""

from .common import EdiProductCase


class TestProduct(EdiProductCase):
    """EDI product tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        EdiRecordType = cls.env["edi.record.type"]
        EdiDocumentType = cls.env["edi.document.type"]
        IrModel = cls.env["ir.model"]
        cls.rec_type_product = EdiRecordType.create(
            {
                "name": "Dummy product record",
                "model_id": IrModel._get_id("edi.product.record"),
            }
        )
        cls.doc_type_product = EdiDocumentType.create(
            {
                "name": "Dummy product document",
                "model_id": IrModel._get_id("edi.product.document"),
                "rec_type_ids": [(6, 0, [cls.rec_type_product.id])],
            }
        )

    def test_empty(self):
        """Test document with no input attachments"""
        EdiDocument = self.env["edi.document"]
        doc = EdiDocument.create(
            {
                "name": "Empty product test",
                "doc_type_id": self.doc_type_product.id,
            }
        )
        with self.assertRaisesIssue(doc):
            doc.action_prepare()

    def test_dummy(self):
        """Test document with dummy input attachment"""
        EdiDocument = self.env["edi.document"]
        doc = EdiDocument.create(
            {
                "name": "Dummy product test",
                "doc_type_id": self.doc_type_product.id,
            }
        )
        self.create_input_attachment(doc, "dummy.txt")
        doc.action_execute()
