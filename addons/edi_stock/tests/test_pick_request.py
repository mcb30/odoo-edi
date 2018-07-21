"""EDI stock transfer request tests"""

from .common import EdiPickRequestCase


class TestPickRequest(EdiPickRequestCase):
    """EDI stock transfer request tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        EdiRecordType = cls.env['edi.record.type']
        EdiDocumentType = cls.env['edi.document.type']
        IrModel = cls.env['ir.model']
        cls.rec_type_pick_request = EdiRecordType.create({
            'name': "Dummy stock transfer request record",
            'model_id': IrModel._get_id('edi.pick.request.record'),
        })
        cls.rec_type_move_request = EdiRecordType.create({
            'name': "Dummy stock move request record",
            'model_id': IrModel._get_id('edi.move.request.record'),
        })
        cls.doc_type_pick_request = EdiDocumentType.create({
            'name': "Dummy stock transfer request document",
            'model_id': IrModel._get_id('edi.pick.request.document'),
            'rec_type_ids': [(6, 0, [cls.rec_type_pick_request.id,
                                     cls.rec_type_move_request.id])],
        })

    def test01_empty(self):
        """Test document with no input attachments"""
        EdiDocument = self.env['edi.document']
        doc = EdiDocument.create({
            'name': "Empty stock transfer request test",
            'doc_type_id': self.doc_type_pick_request.id,
        })
        with self.assertRaisesIssue(doc):
            doc.action_prepare()

    def test02_dummy(self):
        """Test document with dummy input attachment"""
        EdiDocument = self.env['edi.document']
        doc = EdiDocument.create({
            'name': "Dummy stock transfer request test",
            'doc_type_id': self.doc_type_pick_request.id,
        })
        self.create_input_attachment(doc, 'dummy.txt')
        doc.action_execute()
