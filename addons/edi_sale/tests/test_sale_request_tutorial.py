"""EDI sale order request tutorial tests"""

from .common import EdiSaleCase


class TestTutorial(EdiSaleCase):
    """EDI sale order request tutorial tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sale_request_tutorial_record_type = cls.env.ref(
            "edi_sale.sale_request_tutorial_record_type"
        )
        cls.sale_line_request_tutorial_record_type = cls.env.ref(
            "edi_sale.sale_line_request_tutorial_record_type"
        )
        cls.doc_type_tutorial = cls.env.ref("edi_sale.sale_request_tutorial_document_type")
        cls.doc_type_tutorial.active = True
        cls.sale_request_tutorial_record_type.active = True
        cls.sale_line_request_tutorial_record_type.active = True

    @classmethod
    def create_tutorial(cls, *filenames):
        """Create sale order request tutorial document"""
        return cls.create_input_document(cls.doc_type_tutorial, *filenames)

    def test_basic(self):
        """Basic document execution"""
        doc = self.create_tutorial("order01.csv")
        self.assertTrue(doc.action_execute())
        customers = doc.mapped("partner_ids.partner_id")
        self.assertEqual(len(customers), 2)
        self.assertEqual(set(customers.mapped("name")), set(["Alice", "Bob"]))
        sales = doc.mapped("sale_request_tutorial_ids.sale_id")
        self.assertEqual(len(sales), 3)
        self.assertEqual(doc.sale_ids, sales)
        for sale in sales:
            self.assertEqual(sale.state, "sale")
        sales_by_name = {x.origin: x for x in sales}
        self.assertEqual(sales_by_name["ORD01"].partner_id.name, "Alice")
        self.assertEqual(len(sales_by_name["ORD01"].order_line), 2)
        self.assertEqual(len(sales_by_name["ORD02"].order_line), 1)
        self.assertEqual(sales_by_name["ORD02"].order_line.product_id, self.cherry)
        self.assertEqual(sales_by_name["ORD02"].order_line.product_uom_qty, 7)
        self.assertEqual(sales_by_name["ORD03"].partner_id.name, "Bob")
        self.assertEqual(len(sales_by_name["ORD03"].order_line), 1)
        self.assertEqual(sales_by_name["ORD03"].order_line.product_id, self.apple)
        self.assertEqual(sales_by_name["ORD03"].order_line.product_uom_qty, 198)
