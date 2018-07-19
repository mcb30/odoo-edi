"""EDI orderpoint tests"""

from .common import EdiOrderpointCase


class TestOrderpoint(EdiOrderpointCase):
    """EDI orderpoint tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        EdiRecordType = cls.env['edi.record.type']
        EdiDocumentType = cls.env['edi.document.type']
        IrModel = cls.env['ir.model']
        cls.rec_type_orderpoint = EdiRecordType.create({
            'name': "Dummy orderpoint record",
            'model_id': IrModel._get_id('edi.orderpoint.record'),
        })
        cls.doc_type_orderpoint = EdiDocumentType.create({
            'name': "Dummy orderpoint document",
            'model_id': IrModel._get_id('edi.orderpoint.document'),
            'rec_type_ids': [(6, 0, [cls.rec_type_orderpoint.id])],
        })

    def test01_empty(self):
        """Test document with no input attachments"""
        EdiDocument = self.env['edi.document']
        doc = EdiDocument.create({
            'name': "Empty orderpoint test",
            'doc_type_id': self.doc_type_orderpoint.id,
        })
        with self.assertRaisesIssue(doc):
            doc.action_prepare()

    def test02_dummy(self):
        """Test document with dummy input attachment"""
        EdiDocument = self.env['edi.document']
        doc = EdiDocument.create({
            'name': "Dummy orderpoint test",
            'doc_type_id': self.doc_type_orderpoint.id,
        })
        self.create_input_attachment(doc, 'dummy.txt')
        doc.action_execute()
