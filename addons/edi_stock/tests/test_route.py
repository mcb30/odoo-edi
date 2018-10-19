"""EDI stock route tests"""

from .common import EdiCase


class TestRoute(EdiCase):
    """EDI stock route tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        EdiRecordType = cls.env['edi.record.type']
        EdiDocumentType = cls.env['edi.document.type']
        IrModel = cls.env['ir.model']
        cls.rec_type_route = cls.env.ref('edi_stock.route_record_type')
        cls.doc_type_route = EdiDocumentType.create({
            'name': "Dummy stock route document",
            'model_id': IrModel._get_id('edi.route.document'),
            'rec_type_ids': [(6, 0, [cls.rec_type_route.id])],
        })

    def test01_route(self):
        """Test stock route document with dummy input attachment"""
        EdiDocument = self.env['edi.document']
        doc = EdiDocument.create({
            'name': "Dummy stock route test",
            'doc_type_id': self.doc_type_route.id,
        })
        self.create_input_attachment(doc, 'dummy.txt')
        doc.action_execute()
