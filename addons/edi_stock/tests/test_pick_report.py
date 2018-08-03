"""EDI stock transfer report tests"""

from .common import EdiPickCase


class TestPickReport(EdiPickCase):
    """EDI stock transfer report tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        EdiRecordType = cls.env['edi.record.type']
        EdiDocumentType = cls.env['edi.document.type']
        IrModel = cls.env['ir.model']
        cls.rec_type_pick_report = EdiRecordType.create({
            'name': "Dummy stock transfer report record",
            'model_id': IrModel._get_id('edi.pick.report.record'),
        })
        cls.rec_type_move_report = EdiRecordType.create({
            'name': "Dummy stock move report record",
            'model_id': IrModel._get_id('edi.move.report.record'),
        })
        cls.pick_type_in = cls.env.ref('stock.picking_type_in')
        cls.doc_type_pick_report = EdiDocumentType.create({
            'name': "Dummy stock transfer report document",
            'model_id': IrModel._get_id('edi.pick.report.document'),
            'rec_type_ids': [(6, 0, [cls.rec_type_pick_report.id,
                                     cls.rec_type_move_report.id])],
            'pick_type_ids': [(6, 0, [cls.pick_type_in.id])],
        })
        cls.pick_in = cls.create_pick(cls.pick_type_in)
        cls.create_move(cls.pick_in, cls.apple, 5)
        cls.create_move(cls.pick_in, cls.banana, 7)

    def test01_empty(self):
        """Test document with no pickings"""
        EdiDocument = self.env['edi.document']
        EdiPickReport = self.env['edi.pick.report.record']
        EdiMoveReport = self.env['edi.move.report.record']
        doc = EdiDocument.create({
            'name': "Empty stock transfer report test",
            'doc_type_id': self.doc_type_pick_report.id,
        })
        self.assertTrue(doc.action_execute())
        pick_reports = EdiPickReport.search([('doc_id', '=', doc.id)])
        move_reports = EdiMoveReport.search([('doc_id', '=', doc.id)])
        self.assertFalse(pick_reports)
        self.assertFalse(move_reports)

    def test02_dummy(self):
        """Test document with dummy picking"""
        EdiDocument = self.env['edi.document']
        EdiPickReport = self.env['edi.pick.report.record']
        EdiMoveReport = self.env['edi.move.report.record']
        self.complete_pick(self.pick_in)
        doc = EdiDocument.create({
            'name': "Dummy stock transfer report test",
            'doc_type_id': self.doc_type_pick_report.id,
        })
        self.assertTrue(doc.action_execute())
        self.assertEqual(self.pick_in.edi_pick_report_id, doc)
        pick_reports = EdiPickReport.search([('doc_id', '=', doc.id)])
        move_reports = EdiMoveReport.search([('doc_id', '=', doc.id)])
        self.assertEqual(pick_reports.mapped('pick_id'), self.pick_in)
        self.assertEqual(move_reports.mapped('move_ids'),
                         self.pick_in.move_lines)
        move_reports_by_product = {x.product_id.default_code: x
                                   for x in move_reports}
        self.assertEqual(move_reports_by_product['APPLE'].qty, 5)
        self.assertEqual(move_reports_by_product['BANANA'].qty, 7)
