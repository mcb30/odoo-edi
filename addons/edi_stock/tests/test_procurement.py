"""EDI procurement rule tests"""

from .common import EdiCase


class TestProcurement(EdiCase):
    """EDI procurement rule tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        EdiRecordType = cls.env["edi.record.type"]
        EdiDocumentType = cls.env["edi.document.type"]
        IrModel = cls.env["ir.model"]
        cls.rec_type_procurement = cls.env.ref("edi_stock.procurement_record_type")
        cls.doc_type_procurement = EdiDocumentType.create(
            {
                "name": "Dummy procurement rule document",
                "model_id": IrModel._get_id("edi.procurement.document"),
                "rec_type_ids": [(6, 0, [cls.rec_type_procurement.id])],
            }
        )

    def test01_procurement(self):
        """Test procurement rule document with dummy input attachment"""
        EdiDocument = self.env["edi.document"]
        doc = EdiDocument.create(
            {
                "name": "Dummy procurement rule test",
                "doc_type_id": self.doc_type_procurement.id,
            }
        )
        self.create_input_attachment(doc, "dummy.txt")
        doc.action_execute()
