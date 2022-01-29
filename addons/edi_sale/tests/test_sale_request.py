"""EDI sale order request tests"""

from .common import EdiSaleCase


class TestSaleRequest(EdiSaleCase):
    """EDI sale order request tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        EdiRecordType = cls.env["edi.record.type"]
        EdiDocumentType = cls.env["edi.document.type"]
        IrModel = cls.env["ir.model"]
        cls.rec_type_sale_request = EdiRecordType.create(
            {
                "name": "Dummy sale line request record",
                "model_id": IrModel._get_id("edi.sale.request.record"),
            }
        )
        cls.rec_type_sale_line_request = EdiRecordType.create(
            {
                "name": "Dummy sale line request record",
                "model_id": IrModel._get_id("edi.sale.line.request.record"),
            }
        )
        cls.doc_type_sale_request = EdiDocumentType.create(
            {
                "name": "Dummy sale request document",
                "model_id": IrModel._get_id("edi.sale.request.document"),
                "rec_type_ids": [
                    (6, 0, [cls.rec_type_sale_request.id, cls.rec_type_sale_line_request.id])
                ],
            }
        )

    def test01_empty(self):
        """Test document with no input attachments"""
        EdiDocument = self.env["edi.document"]
        doc = EdiDocument.create(
            {
                "name": "Empty sale request test",
                "doc_type_id": self.doc_type_sale_request.id,
            }
        )
        with self.assertRaisesIssue(doc):
            doc.action_prepare()

    def test02_dummy(self):
        """Test document with dummy input attachment"""
        EdiDocument = self.env["edi.document"]
        doc = EdiDocument.create(
            {
                "name": "Dummy sale request test",
                "doc_type_id": self.doc_type_sale_request.id,
            }
        )
        self.create_input_attachment(doc, "dummy.txt")
        doc.action_execute()
