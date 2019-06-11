"""EDI partner tutorial tests"""

from .common import EdiCase


class TestPartnerTutorial(EdiCase):
    """EDI partner tutorial tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc_type_tutorial = cls.env.ref(
            'edi.partner_tutorial_document_type'
        )

    @classmethod
    def create_tutorial(cls, *filenames):
        """Create partner tutorial document"""
        return cls.create_input_document(cls.doc_type_tutorial, *filenames)

    def test01_basic(self):
        """Basic document execution"""
        doc = self.create_tutorial('friends.csv')
        self.assertTrue(doc.action_execute())
        partners = doc.mapped('partner_tutorial_ids.partner_id')
        self.assertEqual(len(partners), 4)
        partners_by_ref = {x.ref: x for x in partners}
        self.assertEqual(partners_by_ref['A'].name, 'Alice')
        self.assertEqual(partners_by_ref['B'].email, 'bob@example.com')
        self.assertEqual(partners_by_ref['E'].title.name, 'Ms')
        self.assertFalse(partners_by_ref['U'].title)

    def test02_identical(self):
        """Document and subsequent identical document"""
        doc1 = self.create_tutorial('friends.csv')
        self.assertTrue(doc1.action_execute())
        self.assertEqual(len(doc1.partner_tutorial_ids), 4)
        doc2 = self.create_tutorial('friends.csv')
        self.assertTrue(doc2.action_execute())
        self.assertEqual(len(doc2.partner_tutorial_ids), 0)

    def test03_correction(self):
        """Document and subsequent correction document"""
        doc1 = self.create_tutorial('friends.csv')
        self.assertTrue(doc1.action_execute())
        partners = doc1.mapped('partner_tutorial_ids.partner_id')
        self.assertEqual(len(partners), 4)
        partners.filtered(lambda x: x.ref == 'E').email = 'eve@example.org'
        doc2 = self.create_tutorial('friends.csv')
        self.assertTrue(doc2.action_execute())
        partners = doc2.mapped('partner_tutorial_ids.partner_id')
        self.assertEqual(len(partners), 1)
        self.assertEqual(partners.ref, 'E')
        self.assertEqual(partners.email, 'eve@example.com')

    def test03_correction(self):
        """Document and subsequent correction document"""
        Title = self.env['res.partner.title']
        doc1 = self.create_tutorial('friends.csv')
        self.assertTrue(doc1.action_execute())
        partners = doc1.mapped('partner_tutorial_ids.partner_id')
        self.assertEqual(len(partners), 4)
        doc2 = self.create_tutorial('update_untitled.csv')
        self.assertTrue(doc2.action_prepare())
        dame_title = Title.create({'name': 'Dame', 'shortcut': 'Dm'})
        self.assertTrue(doc2.action_execute())
        partners = doc2.mapped('partner_tutorial_ids.partner_id')
        self.assertEqual(len(partners), 1)
        self.assertEqual(partners.ref, 'U')
        self.assertEqual(partners.email, 'untitled@example.com')
        self.assertTrue(partners.title, dame_title)
