"""EDI stock location tests"""

from .common import EdiCase


class TestLocation(EdiCase):
    """EDI stock location tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        EdiRecordType = cls.env["edi.record.type"]
        EdiDocumentType = cls.env["edi.document.type"]
        IrModel = cls.env["ir.model"]
        cls.rec_type_location = cls.env.ref("edi_stock.location_record_type")
        cls.doc_type_location = EdiDocumentType.create(
            {
                "name": "Dummy stock location document",
                "model_id": IrModel._get_id("edi.location.document"),
                "rec_type_ids": [(6, 0, [cls.rec_type_location.id])],
            }
        )

    def test_location(self):
        """Test stock location document with dummy input attachment"""
        EdiDocument = self.env["edi.document"]
        doc = EdiDocument.create(
            {
                "name": "Dummy stock location test",
                "doc_type_id": self.doc_type_location.id,
            }
        )
        self.create_input_attachment(doc, "dummy.txt")
        doc.action_execute()
