"""EDI orderpoint tests"""

from odoo.addons.edi.tests.common import EdiCase


class EdiOrderpointCase(EdiCase):
    """Base test case for EDI orderpoint models"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create test products
        Product = cls.env['product.product']
        cls.apple = Product.create({
            'default_code': 'APPLE',
            'name': 'Apple',
        })
        cls.banana = Product.create({
            'default_code': 'BANANA',
            'name': 'Banana',
        })
        # Create test locations
        Location = cls.env['stock.location']
        cls.fridge = Location.create({
            'name': 'FRIDGE',
        })
        cls.cupboard = Location.create({
            'name': 'CUPBOARD',
        })


class EdiPickCase(EdiCase):
    """Base test case for EDI stock transfer request models"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create test products
        Product = cls.env['product.product']
        cls.apple = Product.create({
            'default_code': 'APPLE',
            'name': 'Apple',
        })
        cls.banana = Product.create({
            'default_code': 'BANANA',
            'name': 'Banana',
        })
        cls.cherry = Product.create({
            'default_code': 'CHERRY',
            'name': 'Cherry',
        })
        # Ensure picking type definitions are usable for our tests
        cls.loc_suppliers = cls.env.ref('stock.stock_location_suppliers')
        cls.loc_stock = cls.env.ref('stock.stock_location_stock')
        cls.loc_customers = cls.env.ref('stock.stock_location_customers')
        cls.pick_type_in = cls.env.ref('stock.picking_type_in')
        cls.pick_type_in.sequence_id.prefix = 'WH/IN/'
        cls.pick_type_in.default_location_src_id = cls.loc_suppliers
        cls.pick_type_in.default_location_dest_id = cls.loc_stock
        cls.pick_type_out = cls.env.ref('stock.picking_type_out')
        cls.pick_type_out.sequence_id.prefix = 'WH/OUT/'
        cls.pick_type_out.default_location_src_id = cls.loc_stock
        cls.pick_type_out.default_location_dest_id = cls.loc_customers
