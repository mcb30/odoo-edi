"""EDI sale order forward request tests"""

from odoo.addons.edi_sale.tests.common import EdiSaleCase


class TestSaleForwardRequest(EdiSaleCase):
    """EDI sale order request tutorial tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc_type_sale_forward_request = cls.env.ref(
            "edi_sale_forward_request.sale_forward_request_document_type"
        )
        cls.product_ram = cls.env["product.product"].create(
            dict(name="Computer RAM", default_code="CXN789H")
        )
        cls.product_display = cls.env["product.product"].create(
            dict(name="Computer Display", default_code="CXN789U")
        )

    @classmethod
    def create_edi_document(cls, *filenames):
        """Create sale order request tutorial document"""
        return cls.create_input_document(cls.doc_type_sale_forward_request, *filenames)

    def test_basic(self):
        """Basic document execution"""
        doc = self.create_edi_document("order01.json")
        self.assertTrue(doc.action_execute())
        customers = doc.mapped("json_partner_ids.partner_id")
        self.assertEqual(len(customers), 1)
        self.assertEqual(set(customers.mapped("name")), set(["Alice"]))
        sales = doc.mapped("sale_forward_request_ids.sale_id")
        self.assertEqual(len(sales), 1)
        self.assertEqual(doc.sale_ids, sales)
        for sale in sales:
            self.assertEqual(sale.state, "sale")
        sales_by_name = {x.origin: x for x in sales}
        self.assertEqual(sales_by_name["S00010"].partner_id.name, "Alice")
        order_lines = sales_by_name["S00010"].order_line
        self.assertEqual(len(order_lines), 2)
        order_line = order_lines.filtered(lambda r: r.product_id.default_code == "CXN789H")
        self.assertEqual(len(order_line), 1)
        self.assertEqual(order_line.product_uom_qty, 5.0)

        order_line = order_lines.filtered(lambda r: r.product_id.default_code == "CXN789U")
        self.assertEqual(len(order_line), 1)
        self.assertEqual(order_line.product_uom_qty, 7.0)

    def test_invalid_json(self):
        """Test json schema validation with invalid json"""
        doc = self.create_edi_document("order02.json")
        doc.action_execute()
        self.assertEqual(len(doc.issue_ids), 1)
        self.assertTrue("Failed validating" in doc.issue_ids.name)
