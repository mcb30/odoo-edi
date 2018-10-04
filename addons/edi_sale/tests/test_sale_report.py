"""EDI sale order report tests"""

from .common import EdiSaleCase


class TestSaleReport(EdiSaleCase):
    """EDI sale order report tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        EdiDocumentType = cls.env['edi.document.type']
        IrModel = cls.env['ir.model']
        cls.rec_type_sale_report = cls.env.ref(
            'edi_sale.sale_report_record_type'
        )
        cls.rec_type_sale_line_report = cls.env.ref(
            'edi_sale.sale_line_report_record_type'
        )
        cls.doc_type_sale_report = EdiDocumentType.create({
            'name': "Dummy sale order report document",
            'model_id': IrModel._get_id('edi.sale.report.document'),
            'rec_type_ids': [(6, 0, [cls.rec_type_sale_report.id,
                                     cls.rec_type_sale_line_report.id])],
        })
        cls.user = cls.env.ref('base.public_partner')
        cls.sale = cls.create_sale(cls.user)
        cls.create_sale_line(cls.sale, cls.apple, 5)
        cls.create_sale_line(cls.sale, cls.banana, 7)

    def test01_empty(self):
        """Test document with no sale orders"""
        EdiDocument = self.env['edi.document']
        EdiSaleReport = self.env['edi.sale.report.record']
        EdiSaleLineReport = self.env['edi.sale.line.report.record']
        doc = EdiDocument.create({
            'name': "Empty sale order report test",
            'doc_type_id': self.doc_type_sale_report.id,
        })
        self.assertTrue(doc.action_execute())
        sale_reports = EdiSaleReport.search([('doc_id', '=', doc.id)])
        line_reports = EdiSaleLineReport.search([('doc_id', '=', doc.id)])
        self.assertFalse(sale_reports)
        self.assertFalse(line_reports)

    def test02_dummy(self):
        """Test document with dummy sale order"""
        EdiDocument = self.env['edi.document']
        EdiSaleReport = self.env['edi.sale.report.record']
        EdiSaleLineReport = self.env['edi.sale.line.report.record']
        self.complete_sale(self.sale)
        doc = EdiDocument.create({
            'name': "Dummy sale order report test",
            'doc_type_id': self.doc_type_sale_report.id,
        })
        self.assertTrue(doc.action_execute())
        self.assertEqual(self.sale.edi_sale_report_id, doc)
        sale_reports = EdiSaleReport.search([('doc_id', '=', doc.id)])
        line_reports = EdiSaleLineReport.search([('doc_id', '=', doc.id)])
        self.assertEqual(sale_reports.mapped('sale_id'), self.sale)
        self.assertEqual(line_reports.mapped('line_ids'),
                         self.sale.order_line)
        line_reports_by_product = {x.product_id.default_code: x
                                   for x in line_reports}
        self.assertEqual(line_reports_by_product['APPLE'].qty, 5)
        self.assertEqual(line_reports_by_product['BANANA'].qty, 7)

    def test03_duplicate(self):
        """Test attempt to create duplicate sale order report"""
        EdiDocument = self.env['edi.document']
        self.complete_sale(self.sale)
        doc1 = EdiDocument.create({
            'name': "Dummy sale order report test 1",
            'doc_type_id': self.doc_type_sale_report.id,
        })
        doc2 = EdiDocument.create({
            'name': "Dummy sale order report test 2",
            'doc_type_id': self.doc_type_sale_report.id,
        })
        self.assertTrue(doc1.action_prepare())
        self.assertTrue(doc2.action_prepare())
        self.assertTrue(doc1.action_execute())
        with self.assertRaisesIssue(doc2):
            doc2.action_execute()
