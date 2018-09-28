"""EDI stock transfer report tutorial tests"""

from .common import EdiPickCase


class TestTutorial(EdiPickCase):
    """EDI stock transfer report tutorial tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Tracker = cls.env['edi.move.tracker']
        cls.tracker_first = Tracker.create({'name': "ORDER01"})
        cls.tracker_second = Tracker.create({'name': "ORDER02"})
        cls.tracker_third = Tracker.create({'name': "ORDER03"})
        cls.doc_type_tutorial = cls.env.ref(
            'edi_stock.pick_report_tutorial_document_type'
        )
        cls.pick_morning = cls.create_pick(cls.pick_type_in)
        cls.create_move(cls.pick_morning, cls.tracker_first, cls.apple, 5)
        cls.create_move(cls.pick_morning, cls.tracker_first, cls.banana, 7)
        cls.pick_afternoon = cls.create_pick(cls.pick_type_in)
        cls.create_move(cls.pick_afternoon, cls.tracker_second, cls.apple, 58)
        cls.create_move(cls.pick_afternoon, cls.tracker_second, cls.banana, 74)
        cls.create_move(cls.pick_afternoon, cls.tracker_third, cls.cherry, 172)

    @classmethod
    def create_tutorial(cls):
        """Create stock transfer report tutorial document"""
        return cls.create_document(cls.doc_type_tutorial)

    def test01_basic(self):
        """Basic document execution"""
        self.complete_picks(self.pick_morning)
        doc = self.create_tutorial()
        self.assertTrue(doc.action_prepare())
        self.assertEqual(len(doc.output_ids), 0)
        self.assertTrue(doc.action_execute())
        self.assertEqual(len(doc.output_ids), 1)
        self.assertAttachment(doc.output_ids, 'in01.csv',
                              pattern=r'IN\d+\.csv')

    def test02_combined(self):
        """Multiple pickings"""
        self.complete_picks(self.pick_morning)
        self.complete_picks(self.pick_afternoon)
        doc = self.create_tutorial()
        self.assertTrue(doc.action_execute())
        self.assertEqual(len(doc.output_ids), 2)
        (in01, in02) = doc.output_ids.sorted('id')
        self.assertAttachment(in01, 'in01.csv', pattern=r'IN\d+\.csv')
        self.assertAttachment(in02, 'in02.csv', pattern=r'IN\d+\.csv')

    def test03_multiple(self):
        """Multiple reports"""
        self.complete_picks(self.pick_morning)
        doc1 = self.create_tutorial()
        self.assertTrue(doc1.action_execute())
        self.assertEqual(len(doc1.output_ids), 1)
        self.assertAttachment(doc1.output_ids, 'in01.csv',
                              pattern=r'IN\d+\.csv')
        self.complete_picks(self.pick_afternoon)
        doc2 = self.create_tutorial()
        self.assertTrue(doc2.action_execute())
        self.assertEqual(len(doc2.output_ids), 1)
        self.assertAttachment(doc2.output_ids, 'in02.csv',
                              pattern=r'IN\d+\.csv')

    def test04_cancelled_pick(self):
        """Cancelled picks"""
        self.pick_morning.action_cancel()
        self.complete_picks(self.pick_afternoon)
        doc = self.create_tutorial()
        self.assertTrue(doc.action_execute())
        self.assertEqual(len(doc.output_ids), 1)
        self.assertAttachment(doc.output_ids, 'in02.csv',
                              pattern=r'IN\d+\.csv')

    def test05_cancelled_move(self):
        """Cancelled moves"""
        self.pick_morning.move_lines.filtered(
            lambda x: x.product_id == self.apple
        )._action_cancel()
        self.complete_picks(self.pick_morning)
        doc = self.create_tutorial()
        self.assertTrue(doc.action_execute())
        self.assertEqual(len(doc.output_ids), 1)
        self.assertAttachment(doc.output_ids, 'in03.csv',
                              pattern=r'IN\d+\.csv')

    def test06_autoemit(self):
        """Autoemit functionality"""
        self.complete_picks(self.pick_morning)
        doc = self.doc_type_tutorial.autoemit()
        self.assertEqual(len(doc.output_ids), 1)
        self.assertAttachment(doc.output_ids, 'in01.csv',
                              pattern=r'IN\d+\.csv')

    def test07_trigger_autoemit(self):
        """Autoemit functionality triggered on pick completion"""
        self.pick_type_in.edi_pick_report_autoemit = True
        self.complete_picks(self.pick_morning)
        self.complete_picks(self.pick_afternoon)
        doc1 = self.pick_morning.edi_pick_report_id
        doc2 = self.pick_afternoon.edi_pick_report_id
        self.assertTrue(doc1)
        self.assertTrue(doc2)
        self.assertNotEqual(doc1, doc2)
        self.assertEqual(len(doc1.output_ids), 1)
        self.assertEqual(len(doc2.output_ids), 1)
        self.assertAttachment(doc1.output_ids, 'in01.csv',
                              pattern=r'IN\d+\.csv')
        self.assertAttachment(doc2.output_ids, 'in02.csv',
                              pattern=r'IN\d+\.csv')
