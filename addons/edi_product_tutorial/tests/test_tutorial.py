"""EDI product tutorial tests"""

from odoo.addons.edi_product.tests.common import EdiProductCase


class TestTutorial(EdiProductCase):
    """EDI product tutorial tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc_type_tutorial = cls.env.ref("edi_product.tutorial_document_type")
        cls.units = cls.env.ref("uom.product_uom_unit")
        cls.dozens = cls.env.ref("uom.product_uom_dozen")
        cls.dozens.name = "Dozen(s)"

    @classmethod
    def create_tutorial(cls, *filenames):
        """Create product tutorial document"""
        return cls.create_input_document(cls.doc_type_tutorial, *filenames)

    def test01_basic(self):
        """Basic document execution"""
        doc = self.create_tutorial("books01.csv")
        self.assertTrue(doc.action_execute())
        products = doc.mapped("product_tutorial_ids.product_id")
        self.assertEqual(len(products), 3)
        products_by_code = {x.default_code: x for x in products}
        self.assertEqual(products_by_code["9780552146166"].uom_id, self.dozens)
        self.assertEqual(products_by_code["9780552145428"].name, "Hogfather")

    def test02_basic(self):
        """Basic document execution (with fruit)"""
        doc = self.create_tutorial("fruit01.csv")
        self.assertTrue(doc.action_execute())
        products = doc.mapped("product_tutorial_ids.product_id")
        self.assertEqual(len(products), 3)

    def test03_identical(self):
        """Document and subsequent identical document"""
        doc1 = self.create_tutorial("books01.csv")
        self.assertTrue(doc1.action_execute())
        self.assertEqual(len(doc1.product_tutorial_ids), 3)
        doc2 = self.create_tutorial("books01.csv")
        self.assertTrue(doc2.action_execute())
        self.assertEqual(len(doc2.product_tutorial_ids), 0)

    def test04_correction(self):
        """Document and subsequent corrected document"""
        doc1 = self.create_tutorial("books01.csv")
        self.assertTrue(doc1.action_execute())
        self.assertEqual(len(doc1.product_tutorial_ids), 3)
        doc2 = self.create_tutorial("books02.csv")
        self.assertTrue(doc2.action_execute())
        self.assertEqual(len(doc2.product_tutorial_ids), 1)
        product = doc2.product_tutorial_ids.product_id
        self.assertEqual(product.barcode, "9780552146166")
        self.assertEqual(product.uom_id, self.units)
        self.assertEqual(product.name, "The Fifth Elephant")

    def test05_deactivate(self):
        """Deactivation of unmentioned products"""
        doc1 = self.create_tutorial("books02.csv")
        self.assertTrue(doc1.action_execute())
        self.assertEqual(len(doc1.product_tutorial_ids), 3)
        doc2 = self.create_tutorial("books03.csv")
        self.assertTrue(doc2.action_execute())
        self.assertEqual(len(doc2.product_tutorial_ids), 0)
        self.assertEqual(len(doc2.inactive_product_ids), 1)
        product = doc2.inactive_product_ids.target_id
        self.assertEqual(product.barcode, "9780552134651")
        self.assertFalse(product.active)
        self.assertEqual(product.name, "Witches Abroad")

    def test06_reactivate(self):
        """Ability to reactivate deactivated products"""
        doc1 = self.create_tutorial("books02.csv")
        self.assertTrue(doc1.action_execute())
        self.assertEqual(len(doc1.product_tutorial_ids), 3)
        products = doc1.mapped("product_tutorial_ids.product_id")
        products_by_code = {x.default_code: x for x in products}
        product = products_by_code["9780552134651"]
        doc2 = self.create_tutorial("books03.csv")
        self.assertTrue(doc2.action_execute())
        self.assertEqual(len(doc2.inactive_product_ids), 1)
        self.assertEqual(doc2.inactive_product_ids.target_id, product)
        self.assertFalse(product.active)
        doc3 = self.create_tutorial("books02.csv")
        self.assertTrue(doc3.action_execute())
        self.assertEqual(len(doc3.product_tutorial_ids), 1)
        self.assertEqual(doc3.product_tutorial_ids.product_id, product)
        self.assertTrue(product.active)
