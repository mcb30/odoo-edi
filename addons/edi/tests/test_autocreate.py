"""EDI document autocreation tests"""

from odoo.exceptions import UserError
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

    def create_wizard(self, *filenames):
        """Create autocreation wizard"""
        EdiAutocreateWizard = self.env['edi.document.autocreate']
        attachments = self.create_attachment(*filenames)
        wizard = EdiAutocreateWizard.create({
            'input_ids': [(6, 0, attachments.ids)],
        })
        return wizard

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
        EdiDocument = self.env['edi.document']
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
        self.assertEqual(list(docs),
                         list(EdiDocument.search([('id', 'in', docs.ids)])))

    def test03_wizard_create(self):
        """Autocreate via wizard"""
        EdiDocument = self.env['edi.document']
        wizard = self.create_wizard('dummy.txt', 'res.users.csv', 'friends.csv')
        action = wizard.action_create()
        self.assertEqual(len(wizard.input_ids), 3)
        self.assertEqual(len(wizard.doc_ids), 2)
        self.assertEqual(wizard.doc_ids.mapped('input_ids'), wizard.input_ids)
        self.assertEqual(wizard.doc_ids[0].doc_type_id, self.doc_type_unknown)
        self.assertEqual(wizard.doc_ids[0].state, 'draft')
        self.assertEqual(wizard.doc_ids[1].doc_type_id, self.doc_type_raw)
        self.assertEqual(wizard.doc_ids[1].state, 'draft')
        self.assertEqual(EdiDocument.search(action['domain']), wizard.doc_ids)

    def test04_wizard_prepare(self):
        """Autocreate and prepare via wizard"""
        EdiDocument = self.env['edi.document']
        wizard = self.create_wizard('res.users.csv')
        action = wizard.action_prepare()
        self.assertEqual(len(wizard.doc_ids), 1)
        self.assertEqual(wizard.doc_ids.doc_type_id, self.doc_type_raw)
        self.assertEqual(wizard.doc_ids.state, 'prep')
        self.assertEqual(EdiDocument.search(action['domain']), wizard.doc_ids)

    def test05_wizard_execute(self):
        """Autocreate and execute via wizard"""
        EdiDocument = self.env['edi.document']
        wizard = self.create_wizard('res.users.csv')
        action = wizard.action_execute()
        self.assertEqual(len(wizard.doc_ids), 1)
        self.assertEqual(wizard.doc_ids.doc_type_id, self.doc_type_raw)
        self.assertEqual(wizard.doc_ids.state, 'done')
        self.assertEqual(EdiDocument.search(action['domain']), wizard.doc_ids)

    def test06_no_inputs(self):
        """Missing input attachments"""
        wizard = self.create_wizard()
        with self.assertRaises(UserError):
            wizard.action_create()
