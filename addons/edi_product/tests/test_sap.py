"""EDI product SAP IDoc tests"""

from .common import EdiProductCase


class TestSap(EdiProductCase):
    """EDI product SAP IDoc tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc_type_sap = cls.env.ref("edi_product.sap_document_type")

    def create_sap(self, *filenames):
        """Create product SAP IDoc document"""
        EdiDocumentType = self.env["edi.document.type"]
        attachments = self.create_attachment(*filenames)
        doc = EdiDocumentType.autocreate(attachments)
        self.assertEqual(len(doc), 1)
        self.assertEqual(doc.doc_type_id, self.doc_type_sap)
        self.assertEqual(doc.input_ids, attachments)
        return doc

    def test01_basic(self):
        """Basic document execution"""
        doc = self.create_sap("LTESTEDI_00199014", "LTESTEDI_00199015")
        self.assertTrue(doc.action_execute())
        products = doc.mapped("product_sap_ids.product_id")
        self.assertEqual(len(products), 2)
        products_by_barcode = {x.barcode: x for x in products}
        self.assertEqual(products_by_barcode["5055365644456"].name, "Enrobed Mango")
        self.assertEqual(products_by_barcode["5055365625424"].name, "Amaretto Soaked Sultanas")

    def test02_identical(self):
        """Document and subsequent identical document"""
        doc1 = self.create_sap("LTESTEDI_00199014", "LTESTEDI_00199015")
        self.assertTrue(doc1.action_execute())
        self.assertEqual(len(doc1.product_sap_ids), 2)
        doc2 = self.create_sap("LTESTEDI_00199014", "LTESTEDI_00199015")
        self.assertTrue(doc2.action_execute())
        self.assertEqual(len(doc2.product_sap_ids), 0)

    def test03_correction(self):
        """Document and subsequent corrected document"""
        doc1 = self.create_sap("LTESTEDI_00199014", "LTESTEDI_00199015")
        self.assertTrue(doc1.action_execute())
        self.assertEqual(len(doc1.product_sap_ids), 2)
        doc2 = self.create_sap("LTESTEDI_00200015")
        self.assertTrue(doc2.action_execute())
        self.assertEqual(len(doc2.product_sap_ids), 1)
        self.assertEqual(doc2.product_sap_ids.product_id.name, "Tasty Enrobed Mango")
