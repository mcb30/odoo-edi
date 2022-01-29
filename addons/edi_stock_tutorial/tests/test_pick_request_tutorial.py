"""EDI stock transfer request tutorial tests"""

from odoo.addons.edi_stock.tests.common import EdiPickCase


class TestTutorial(EdiPickCase):
    """EDI stock transfer request tutorial tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc_type_tutorial = cls.env.ref("edi_stock.pick_request_tutorial_document_type")

    @classmethod
    def create_tutorial(cls, *filenames):
        """Create stock transfer request tutorial document"""
        return cls.create_input_document(cls.doc_type_tutorial, *filenames)

    def test01_basic(self):
        """Basic document execution"""

        # out01 creates two moves
        doc = self.create_tutorial("out01.csv")
        self.assertTrue(doc.action_execute())
        pick = doc.mapped("pick_request_tutorial_ids.pick_id")
        self.assertEqual(doc.pick_ids, pick)
        self.assertEqual(len(pick), 1)
        self.assertEqual(pick.origin, "ORDER01")
        self.assertEqual(pick.picking_type_id, self.pick_type_out)
        self.assertEqual(pick.location_id, self.loc_stock)
        self.assertEqual(pick.location_dest_id, self.loc_customers)
        moves = pick.move_lines
        self.assertEqual(len(moves), 2)
        self.assertEqual(moves.mapped("picking_type_id"), pick.picking_type_id)
        moves_by_code = {x.product_id.default_code: x for x in moves}
        self.assertEqual(moves_by_code["APPLE"].location_id, self.loc_stock)
        self.assertEqual(moves_by_code["APPLE"].product_uom_qty, 5)
        self.assertEqual(moves_by_code["BANANA"].location_dest_id, self.loc_customers)
        self.assertEqual(moves_by_code["BANANA"].product_uom_qty, 2)
        tracker = moves.mapped("edi_tracker_id")
        self.assertEqual(len(tracker), 1)
        self.assertEqual(tracker.name, "ORDER01")

        # out02 updates both moves
        doc = self.create_tutorial("out02.csv")
        self.assertTrue(doc.action_execute())
        self.assertEqual(moves_by_code["APPLE"].product_uom_qty, 3)
        self.assertEqual(moves_by_code["BANANA"].product_uom_qty, 5)

        # out03 cancels BANANA move
        doc = self.create_tutorial("out03.csv")
        self.assertTrue(doc.action_execute())
        self.assertNotEqual(moves_by_code["APPLE"].state, "cancel")
        self.assertEqual(moves_by_code["BANANA"].state, "cancel")

    def test02_no_match(self):
        """Filename with no matched picking type"""
        doc = self.create_tutorial("out01.csv")
        self.pick_type_out.sequence_id.prefix = "WH/NOTOUT/"
        with self.assertRaisesIssue(doc):
            self.assertFalse(doc.action_prepare())
        self.pick_type_out.sequence_id.prefix = "OUT"
        self.assertTrue(doc.action_prepare())

    def test03_multi_match(self):
        """Filename with multiple matched picking types"""
        doc = self.create_tutorial("out01.csv")
        self.pick_type_in.sequence_id.prefix = "ALSO/OUT/"
        with self.assertRaisesIssue(doc):
            self.assertFalse(doc.action_prepare())
        self.pick_type_out.sequence_id.prefix = "NOTOUT/"
        self.assertTrue(doc.action_prepare())
        pick_types = doc.mapped("pick_request_tutorial_ids.pick_type_id")
        self.assertEqual(len(pick_types), 1)
        self.assertEqual(pick_types, self.pick_type_in)

    def test04_started_picking(self):
        """Picking already started but not validated"""
        doc = self.create_tutorial("out01.csv")
        self.assertTrue(doc.action_execute())
        pick = doc.mapped("pick_request_tutorial_ids.pick_id")
        moves = pick.move_lines
        pick.action_assign()
        for move in moves:
            move.quantity_done = move.product_uom_qty
        doc = self.create_tutorial("out02.csv")
        self.assertTrue(doc.action_prepare())
        with self.assertRaisesIssue(doc):
            doc.action_execute()

    def test05_partially_completed_picking(self):
        """Picking completed but the request partially fulfilled. Creates a
        backorder which can be updated with a new update request
        """
        doc = self.create_tutorial("out01.csv")
        self.assertTrue(doc.action_execute())
        pick = doc.mapped("pick_request_tutorial_ids.pick_id")
        moves = pick.move_lines
        pick.action_assign()
        for move in moves:
            move.quantity_done = 1
        pick.action_done()
        doc = self.create_tutorial("out02.csv")
        self.assertTrue(doc.action_execute())
        moves = doc.mapped("move_request_tutorial_ids.move_id")
        moves_by_code = {x.product_id.default_code: x for x in moves}
        self.assertEqual(moves_by_code["APPLE"].product_uom_qty, 3)
        self.assertEqual(moves_by_code["BANANA"].product_uom_qty, 5)

    def test06_repeat_create(self):
        """Create the same two times"""
        doc = self.create_tutorial("out01.csv")
        self.assertTrue(doc.action_execute())
        doc = self.create_tutorial("out01.csv")
        with self.assertRaisesIssue(doc):
            doc.action_execute()

    def test07_update_without_create(self):
        """Update without create"""
        doc = self.create_tutorial("out02.csv")
        with self.assertRaisesIssue(doc):
            doc.action_execute()

    def test08_cancel_without_create(self):
        """Cancel without create"""
        doc = self.create_tutorial("out03.csv")
        with self.assertRaisesIssue(doc):
            doc.action_execute()

    def test09_no_tracking(self):
        """Input with no tracking key"""
        doc = self.create_tutorial("out01.csv")
        self.assertTrue(doc.action_prepare())
        doc.mapped("move_request_tutorial_ids").write({"tracker_key": False})
        self.assertTrue(doc.action_execute())
        moves = doc.mapped("move_request_tutorial_ids.move_id")
        self.assertEqual(len(moves), 2)
        self.assertFalse(moves.mapped("edi_tracker_id"))

    def test10_multiple_moves(self):
        """Test failure when multiple existing moves found"""
        doc1 = self.create_tutorial("out01.csv")
        self.assertTrue(doc1.action_execute())
        move = doc1.mapped("move_request_tutorial_ids.move_id").filtered(
            lambda x: x.product_id == self.banana
        )
        self.assertEqual(len(move), 1)
        self.assertEqual(move.product_uom_qty, 2)
        move.write(
            {
                "product_uom_qty": 1,
                "product_uom_qty": 1,
            }
        )
        move.copy()
        doc2 = self.create_tutorial("out02.csv")
        with self.assertRaisesIssue(doc2):
            doc2.action_execute()
        move._action_cancel()
        self.assertTrue(doc2.action_execute())
