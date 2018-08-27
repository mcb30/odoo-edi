"""EDI stock level report tutorial tests"""

from .common import EdiQuantCase


class TestTutorial(EdiQuantCase):
    """EDI stock level report tutorial tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc_type_tutorial = cls.env.ref(
            'edi_stock.quant_report_tutorial_document_type'
        )
        cls.create_quant(cls.fridge, cls.apple, 7)
        cls.create_quant(cls.cupboard, cls.apple, 3)
        cls.create_quant(cls.cupboard, cls.banana, 6)
        cls.create_quant(cls.cupboard, cls.cherry, 11)
        cls.create_quant(cls.loc_suppliers, cls.apple, 4)
        cls.create_quant(cls.loc_suppliers, cls.banana, 2)

    @classmethod
    def create_tutorial(cls):
        """Create stock level report tutorial document"""
        return cls.create_document(cls.doc_type_tutorial)

    def test01_basic(self):
        """Basic document execution"""
        doc = self.create_tutorial()
        self.assertTrue(doc.action_prepare())
        self.assertEqual(len(doc.output_ids), 0)
        self.assertTrue(doc.action_execute())
        self.assertEqual(len(doc.output_ids), 1)
        self.assertAttachment(doc.output_ids, 'stock01.csv',
                              pattern=r'STK\d+\.csv')

    def test02_multiple(self):
        """Multiple source locations"""
        self.doc_type_tutorial.location_ids += self.loc_suppliers
        doc = self.create_tutorial()
        self.assertTrue(doc.action_execute())
        self.assertAttachment(doc.output_ids, 'stock02.csv',
                              pattern=r'STK\d+\.csv')
