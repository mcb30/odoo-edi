"""EDI stock transfer request tutorial tests"""

from .common import EdiPickRequestCase


class TestTutorial(EdiPickRequestCase):
    """EDI stock transfer request tutorial tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc_type_tutorial = cls.env.ref(
            'edi_stock.pick_request_tutorial_document_type'
        )

    @classmethod
    def create_tutorial(cls, *filenames):
        """Create stock transfer request tutorial document"""
        return cls.create_input_document(cls.doc_type_tutorial, *filenames)

    def test01_basic(self):
        """Basic document execution"""
        doc = self.create_tutorial('out01.csv')
        self.assertTrue(doc.action_execute())
        pick = doc.mapped('pick_request_tutorial_ids.pick_id')
        self.assertEqual(len(pick), 1)
        self.assertEqual(pick.origin, 'out01')
        self.assertEqual(pick.picking_type_id, self.pick_type_out)
        self.assertEqual(pick.location_id, self.loc_stock)
        self.assertEqual(pick.location_dest_id, self.loc_customers)
        moves = pick.move_lines
        self.assertEqual(len(moves), 2)
        moves_by_code = {x.product_id.default_code: x for x in moves}
        self.assertEqual(moves_by_code['APPLE'].location_id, self.loc_stock)
        self.assertEqual(moves_by_code['APPLE'].product_uom_qty, 5)
        self.assertEqual(moves_by_code['BANANA'].location_dest_id,
                         self.loc_customers)
        self.assertEqual(moves_by_code['BANANA'].product_uom_qty, 2)
