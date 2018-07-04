"""EDI product tests"""

from .common import EdiProductCase


class TestProduct(EdiProductCase):
    """EDI product tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        EdiDocumentType = cls.env['edi.document.type']
        IrModel = cls.env['ir.model']
        cls.doc_type_product = EdiDocumentType.create({
            'name': "Dummy product document",
            'model_id': IrModel._get_id('edi.product.document'),
            'rec_type_ids': [6, 0, IrModel._get_id('edi.product.record')],
        })

    def test01_empty(self):
        """Test document with no input attachments"""
        EdiDocument = self.env['edi.document']
        doc = EdiDocument.create({
            'name': "Empty product test",
            'doc_type_id': self.doc_type_product.id,
        })
        with self.assertRaisesIssue(doc):
            doc.action_prepare()

    def test02_dummy(self):
        """Test document with dummy input attachment"""
        EdiDocument = self.env['edi.document']
        doc = EdiDocument.create({
            'name': "Dummy product test",
            'doc_type_id': self.doc_type_product.id,
        })
        self.create_input_attachment(doc, 'dummy.txt')
        doc.action_execute()
