"""EDI sale order tests"""

from odoo.addons.edi.tests.common import EdiCase


class EdiSaleCase(EdiCase):
    """Base test case for EDI sale order models"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create test products
        Product = cls.env['product.product']
        cls.apple = Product.create({
            'default_code': 'APPLE',
            'name': 'Apple',
            'list_price': 0.70,
        })
        cls.banana = Product.create({
            'default_code': 'BANANA',
            'name': 'Banana',
            'list_price': 0.20,
        })
        cls.cherry = Product.create({
            'default_code': 'CHERRY',
            'name': 'Cherry',
            'list_price': 0.04,
        })

    @classmethod
    def create_sale_line(cls, sale, product, qty, **kwargs):
        """Create a sale order line and attach it a sale order"""
        create_values = {
            'name': product.name,
            'order_id': sale.id,
            'product_id': product.id,
            'product_uom_qty': qty,
            'product_uom': product.uom_id.id,
            'price_unit': product.list_price,
        }
        create_values.update(kwargs)
        return cls.env['sale.order.line'].create(create_values)

    @classmethod
    def create_sale(cls, customer, **kwargs):
        """Create a sale order"""
        create_values = {
            'partner_id': customer.id,
            'partner_invoice_id': customer.id,
            'partner_shipping_id': customer.id,
            'pricelist_id': cls.env.ref('product.list0').id,
        }
        create_values.update(kwargs)
        return cls.env['sale.order'].create(create_values)

    @classmethod
    def complete_sale(cls, sale):
        """Complete a sale order"""
        for line in sale.order_line:
            line.qty_delivered = line.product_uom_qty
        sale.action_done()
