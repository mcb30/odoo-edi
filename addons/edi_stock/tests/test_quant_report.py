"""EDI stock level report tests"""

from .common import EdiQuantCase


class TestQuantReport(EdiQuantCase):
    """EDI stock level report tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        EdiDocumentType = cls.env["edi.document.type"]
        IrModel = cls.env["ir.model"]
        cls.rec_type_quant_report = cls.env.ref("edi_stock.quant_report_record_type")
        cls.doc_type_quant_report = EdiDocumentType.create(
            {
                "name": "Dummy stock level report document",
                "model_id": IrModel._get_id("edi.quant.report.document"),
                "rec_type_ids": [(6, 0, [cls.rec_type_quant_report.id])],
                "location_ids": [(6, 0, [cls.loc_stock.id])],
            }
        )

    def test_empty(self):
        """Test document with no stock"""
        EdiDocument = self.env["edi.document"]
        EdiQuantReport = self.env["edi.quant.report.record"]
        doc = EdiDocument.create(
            {
                "name": "Empty stock level report test",
                "doc_type_id": self.doc_type_quant_report.id,
            }
        )
        self.assertTrue(doc.action_execute())
        quant_reports = EdiQuantReport.search([("doc_id", "=", doc.id)])
        self.assertFalse(quant_reports)

    def test_dummy(self):
        """Test document with dummy stock"""
        EdiDocument = self.env["edi.document"]
        EdiQuantReport = self.env["edi.quant.report.record"]
        self.create_quant(self.fridge, self.apple, 8)
        self.create_quant(self.cupboard, self.banana, 3)
        self.create_quant(self.loc_suppliers, self.banana, 4)
        doc = EdiDocument.create(
            {
                "name": "Dummy stock level report test",
                "doc_type_id": self.doc_type_quant_report.id,
            }
        )
        self.assertTrue(doc.action_execute())
        quant_reports = EdiQuantReport.search([("doc_id", "=", doc.id)])
        self.assertEqual(len(quant_reports), 2)
        quant_reports_by_product = {x.product_id.default_code: x for x in quant_reports}
        self.assertEqual(quant_reports_by_product["APPLE"].qty, 8)
        self.assertEqual(quant_reports_by_product["BANANA"].qty, 3)
