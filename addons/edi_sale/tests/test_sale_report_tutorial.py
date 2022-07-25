"""EDI sale order report tutorial tests"""

from .common import EdiSaleCase


class TestTutorial(EdiSaleCase):
    """EDI sale order report tutorial tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sale_report_tutorial_record_type = cls.env.ref("edi_sale.sale_report_tutorial_record_type")
        cls.sale_line_report_tutorial_record_type = cls.env.ref("edi_sale.sale_line_report_tutorial_record_type")
        cls.doc_type_tutorial = cls.env.ref("edi_sale.sale_report_tutorial_document_type")
        cls.doc_type_tutorial.active = True
        cls.sale_report_tutorial_record_type.active = True
        cls.sale_line_report_tutorial_record_type.active = True
        Partner = cls.env['res.partner']
        cls.alice = Partner.create({
            'name': 'Alice',
        })
        cls.fruit_salad = cls.create_sale(cls.alice, name='SALAD')
        cls.create_sale_line(cls.fruit_salad, cls.apple, 3)
        cls.create_sale_line(cls.fruit_salad, cls.banana, 1)
        cls.create_sale_line(cls.fruit_salad, cls.cherry, 8)

    @classmethod
    def create_tutorial(cls):
        """Create sale order report tutorial document"""
        return cls.create_document(cls.doc_type_tutorial)

    def test01_basic(self):
        """Basic document execution"""
        self.complete_sale(self.fruit_salad)
        doc = self.create_tutorial()
        self.assertTrue(doc.action_prepare())
        self.assertEqual(len(doc.output_ids), 0)
        self.assertTrue(doc.action_execute())
        self.assertEqual(len(doc.output_ids), 1)
        self.assertAttachment(doc.output_ids, 'salad01.csv',
                              pattern=r'SALAD.csv')
