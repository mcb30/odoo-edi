"""EDI stock move tracker tests"""

from .common import EdiPickCase


class TestMoveTracker(EdiPickCase):
    """EDI stock move tracker tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Tracker = cls.env['edi.move.tracker']
        cls.tracker_red = Tracker.create({'name': "Red"})
        cls.tracker_yellow = Tracker.create({'name': "Yellow"})
        cls.tracker_green = Tracker.create({'name': "Green"})

    def test01_pick_ids(self):
        """Test associated stock transfer calculation"""
        first = self.create_pick(self.pick_type_in)
        self.create_move(first, self.tracker_red, self.apple, 3)
        self.create_move(first, self.tracker_yellow, self.banana, 5)
        second = self.create_pick(self.pick_type_in)
        self.create_move(second, self.tracker_red, self.apple, 8)
        self.assertEqual(self.tracker_red.pick_ids, (first | second))
        self.assertEqual(self.tracker_yellow.pick_ids, first)
        self.assertFalse(self.tracker_green.pick_ids)
