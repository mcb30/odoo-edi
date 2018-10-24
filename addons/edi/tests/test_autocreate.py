"""EDI document autocreation tests"""

from .common import EdiCase


class TestAutocreate(EdiCase):
    """EDI document autocreation tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc_type_unknown = cls.env.ref('edi.document_type_unknown')
        cls.doc_type_raw = cls.env.ref('edi.raw_document_type')

    def autocreate(self, *filenames):
        """Autocreate documents"""
        EdiDocumentType = self.env['edi.document.type']
        attachments = self.create_attachment(*filenames)
        self.assertEqual(attachments.mapped('datas_fname'), list(filenames))
        docs = EdiDocumentType.autocreate(attachments)
        return docs

    def test01_basic(self):
        """Basic autocreation"""
        doc1 = self.autocreate('dummy.txt')
        self.assertEqual(len(doc1), 1)
        self.assertEqual(doc1.doc_type_id, self.doc_type_unknown)
        doc2 = self.autocreate('res.users.csv')
        self.assertEqual(len(doc2), 1)
        self.assertEqual(doc2.doc_type_id, self.doc_type_raw)

    def test02_order(self):
        """Order of autocreated documents"""
        docs = self.autocreate('dummy.txt', 'res.users.csv', 'hello_world.txt')
        self.assertEqual(len(docs), 2)
        self.assertEqual(docs[0].input_ids.sorted('id').mapped('datas_fname'),
                         ['dummy.txt', 'hello_world.txt'])
        self.assertEqual(docs[1].input_ids.sorted('id').mapped('datas_fname'),
                         ['res.users.csv'])
        docs = self.autocreate('res.users.csv', 'dummy.txt', 'hello_world.txt')
        self.assertEqual(len(docs), 2)
        self.assertEqual(docs[0].input_ids.sorted('id').mapped('datas_fname'),
                         ['res.users.csv'])
        self.assertEqual(docs[1].input_ids.sorted('id').mapped('datas_fname'),
                         ['dummy.txt', 'hello_world.txt'])
