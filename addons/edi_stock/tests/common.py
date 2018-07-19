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
