"""EDI sale order tests"""

from odoo.addons.edi.tests.common import EdiCase


class EdiSaleCase(EdiCase):
    """Base test case for EDI sale order models"""

    @classmethod
    def create_sale_line(cls, sale, product, qty):
        """Create a sale order line and attach it a sale order"""
        return cls.env['sale.order.line'].create({
            'name': product.name,
            'order_id': sale.id,
            'product_id': product.id,
            'product_uom_qty': qty,
            'product_uom': product.uom_id.id,
            'price_unit': product.list_price,
        })

    @classmethod
    def create_sale(cls, customer):
        """Create a sale order"""
        return cls.env['sale.order'].create({
            'partner_id': customer.id,
            'partner_invoice_id': customer.id,
            'partner_shipping_id': customer.id,
            'pricelist_id': cls.env.ref('product.list0').id,
            'picking_policy': 'direct',
        })
