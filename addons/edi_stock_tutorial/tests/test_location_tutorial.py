"""EDI stock location tutorial tests"""

from odoo.addons.edi.tests.common import EdiCase


class TestLocationTutorial(EdiCase):
    """EDI stock location tutorial tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc_type_tutorial = cls.env.ref("edi_stock.location_tutorial_document_type")

    @classmethod
    def create_tutorial(cls, *filenames):
        """Create stock location tutorial document"""
        return cls.create_input_document(cls.doc_type_tutorial, *filenames)

    def test_basic(self):
        """Basic document execution"""
        doc = self.create_tutorial("places.csv")
        self.assertTrue(doc.action_execute())
        locs = doc.mapped("location_tutorial_ids.location_id")
        self.assertEqual(len(locs), 7)
        locs_by_code = {x.barcode: x for x in locs}
        self.assertEqual(locs_by_code["LOC001"].name, "Location One")
        self.assertEqual(locs_by_code["LOC002"].posy, 20)
        self.assertEqual(locs_by_code["LOC003"].barcode, "LOC003")
        self.assertEqual(locs_by_code["LOC101"].location_id, locs_by_code["ZONE01"])

    def test_identical(self):
        """Document and subsequent identical document"""
        doc1 = self.create_tutorial("places.csv")
        self.assertTrue(doc1.action_execute())
        self.assertEqual(len(doc1.location_tutorial_ids), 7)
        doc2 = self.create_tutorial("places.csv")
        self.assertTrue(doc2.action_execute())
        self.assertEqual(len(doc2.location_tutorial_ids), 0)
