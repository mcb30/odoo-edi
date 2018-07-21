"""EDI orderpoint tutorial tests"""

from .common import EdiOrderpointCase


class TestTutorial(EdiOrderpointCase):
    """EDI orderpoint tutorial tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc_type_tutorial = cls.env.ref(
            'edi_stock.orderpoint_tutorial_document_type'
        )

    @classmethod
    def create_tutorial(cls, *filenames):
        """Create orderpoint tutorial document"""
        return cls.create_input_document(cls.doc_type_tutorial, *filenames)

    def test01_basic(self):
        """Basic document execution"""
        doc = self.create_tutorial('fruit01.csv')
        self.assertTrue(doc.action_execute())
        orderpoints = doc.mapped('orderpoint_tutorial_ids.orderpoint_id')
        self.assertEqual(len(orderpoints), 3)
        orderpoints_by_key = {
            (x.product_id.default_code, x.location_id.name): x
            for x in orderpoints
        }
        self.assertEqual(
            orderpoints_by_key[('APPLE', 'FRIDGE')].product_max_qty, 8
        )
        self.assertEqual(
            orderpoints_by_key[('BANANA', 'CUPBOARD')].product_min_qty, 5
        )
        self.assertEqual(
            orderpoints_by_key[('BANANA', 'CUPBOARD')].lead_days, 14
        )

    def test02_identical(self):
        """Document and subsequent identical document"""
        doc1 = self.create_tutorial('fruit01.csv')
        self.assertTrue(doc1.action_execute())
        self.assertEqual(len(doc1.orderpoint_tutorial_ids), 3)
        doc2 = self.create_tutorial('fruit01.csv')
        self.assertTrue(doc2.action_execute())
        self.assertEqual(len(doc2.orderpoint_tutorial_ids), 0)

    def test03_correction(self):
        """Document and subsequent corrected document"""
        doc1 = self.create_tutorial('fruit01.csv')
        self.assertTrue(doc1.action_execute())
        self.assertEqual(len(doc1.orderpoint_tutorial_ids), 3)
        doc2 = self.create_tutorial('fruit02.csv')
        self.assertTrue(doc2.action_execute())
        self.assertEqual(len(doc2.orderpoint_tutorial_ids), 1)
        orderpoint = doc2.orderpoint_tutorial_ids.orderpoint_id
        self.assertEqual(orderpoint.product_id.default_code, 'APPLE')
        self.assertEqual(orderpoint.product_max_qty, 2)

    def test04_multiple_inheritance(self):
        """Document prepared before all products and locations are created"""
        self.apple.default_code = 'NOT AN APPLE'
        self.fridge.name = 'FREEZER'
        doc = self.create_tutorial('fruit01.csv')
        self.assertTrue(doc.action_prepare())
        with self.assertRaisesIssue(doc):
            doc.action_execute()
        self.apple.default_code = 'APPLE'
        self.fridge.name = 'FRIDGE'
        self.assertTrue(doc.action_execute())
