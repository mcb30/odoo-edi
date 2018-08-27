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
            'type': 'product',
        })
        cls.banana = Product.create({
            'default_code': 'BANANA',
            'name': 'Banana',
            'type': 'product',
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
            'type': 'product',
        })
        cls.banana = Product.create({
            'default_code': 'BANANA',
            'name': 'Banana',
            'type': 'product',
        })
        cls.cherry = Product.create({
            'default_code': 'CHERRY',
            'name': 'Cherry',
            'type': 'product',
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

    @classmethod
    def create_pick(cls, pick_type):
        """Create stock transfer"""
        Picking = cls.env['stock.picking']
        pick = Picking.create({
            'picking_type_id': pick_type.id,
            'location_id': pick_type.default_location_src_id.id,
            'location_dest_id': pick_type.default_location_dest_id.id,
        })
        return pick

    def complete_pick(self, pick):
        """Complete stock transfer"""
        pick.action_confirm()
        for move in pick.move_lines:
            move.quantity_done = move.product_uom_qty
        pick.action_done()
        self.assertEqual(pick.state, 'done')

    @classmethod
    def create_move(cls, pick, tracker, product, qty, **kwargs):
        """Create stock move"""
        Move = cls.env['stock.move']
        vals = {
            'name': product.default_code,
            'picking_id': pick.id,
            'location_id': pick.location_id.id,
            'location_dest_id': pick.location_dest_id.id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': qty,
            'edi_tracker_id': tracker.id if tracker else None,
        }
        vals.update(kwargs)
        move = Move.create(vals)
        return move
