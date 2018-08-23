"""EDI stock transfer report tutorial tests"""

from .common import EdiPickCase


class TestTutorial(EdiPickCase):
    """EDI stock transfer report tutorial tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc_type_tutorial = cls.env.ref(
            'edi_stock.pick_report_tutorial_document_type'
        )
        cls.pick_morning = cls.create_pick(cls.pick_type_in)
        cls.create_move(cls.pick_morning, None, cls.apple, 5)
        cls.create_move(cls.pick_morning, None, cls.banana, 7)
        cls.pick_afternoon = cls.create_pick(cls.pick_type_in)
        cls.create_move(cls.pick_afternoon, None, cls.apple, 58)
        cls.create_move(cls.pick_afternoon, None, cls.banana, 74)
        cls.create_move(cls.pick_afternoon, None, cls.cherry, 172)

    @classmethod
    def create_tutorial(cls):
        """Create stock transfer report tutorial document"""
        return cls.create_document(cls.doc_type_tutorial)

    def test01_basic(self):
        """Basic document execution"""
        self.complete_pick(self.pick_morning)
        doc = self.create_tutorial()
        self.assertTrue(doc.action_execute())
        self.assertEqual(len(doc.output_ids), 1)
        self.assertAttachment(doc.output_ids, 'in01.csv',
                              pattern=r'IN\d+\.csv')

    def test02_combined(self):
        """Multiple pickings"""
        self.complete_pick(self.pick_morning)
        self.complete_pick(self.pick_afternoon)
        doc = self.create_tutorial()
        self.assertTrue(doc.action_execute())
        self.assertEqual(len(doc.output_ids), 2)
        (in01, in02) = doc.output_ids.sorted('id')
        self.assertAttachment(in01, 'in01.csv', pattern=r'IN\d+\.csv')
        self.assertAttachment(in02, 'in02.csv', pattern=r'IN\d+\.csv')

    def test03_multiple(self):
        """Multiple reports"""
        self.complete_pick(self.pick_morning)
        doc1 = self.create_tutorial()
        self.assertTrue(doc1.action_execute())
        self.assertEqual(len(doc1.output_ids), 1)
        self.assertAttachment(doc1.output_ids, 'in01.csv',
                              pattern=r'IN\d+\.csv')
        self.complete_pick(self.pick_afternoon)
        doc2 = self.create_tutorial()
        self.assertTrue(doc2.action_execute())
        self.assertEqual(len(doc2.output_ids), 1)
        self.assertAttachment(doc2.output_ids, 'in02.csv',
                              pattern=r'IN\d+\.csv')
