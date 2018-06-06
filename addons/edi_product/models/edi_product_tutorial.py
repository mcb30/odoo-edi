"""EDI product tutorial

This example shows the code required to implement a simple EDI product
document format comprising a CSV file with a fixed list of columns:

* Product code
* Product description
* Product weight (in grams, optional)
* Product volume (in cubic centimetres, optional)
"""

import csv
from odoo import api, fields, models
from odoo.tools import float_compare


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include EDI product tutorial records"""

    _inherit = 'edi.document'

    product_tutorial_ids = fields.One2many('edi.product.tutorial.record',
                                           'doc_id', string="Products")


class EdiProductTutorialRecord(models.Model):
    """EDI product tutorial record"""

    ROUNDING = 0.01

    _name = 'edi.product.tutorial.record'
    _inherit = 'edi.product.record'
    _description = "Product"

    weight = fields.Integer(string="Weight", required=True, readonly=True,
                            default=0, help="Weight (in grams)")
    volume = fields.Integer(string="Volume", required=True, readonly=True,
                            default=0, help="Volume (in cubic centimetres)")

    @api.multi
    def _product_values(self):
        values = super()._product_values()
        values.update({
            'barcode': self.name,
            'weight': (self.weight / 1000.0),
            'volume': (self.volume / 1000000.0),
        })
        return values

    @api.model
    def _product_changed(self, product, values):
        return (super()._product_changed(product, values) or
                product.barcode != values['name'] or
                float_compare(product.weight, (values['weight'] / 1000.0),
                              precision_rounding=self.ROUNDING) != 0 or
                float_compare(product.volume, (values['volume'] / 1000000.0),
                              precision_rounding=self.ROUNDING) != 0)


class EdiProductTutorialDocument(models.AbstractModel):
    """EDI product tutorial document model"""

    _name = 'edi.product.tutorial.document'
    _inherit = 'edi.product.document'
    _description = "Tutorial product CSV file"

    @api.model
    def _record_values(self, data):
        reader = csv.reader(data.decode().splitlines())
        return ({
            'name': name,
            'description': description,
            'weight': int(weight) if weight else 0,
            'volume': int(volume) if volume else 0,
        } for name, description, weight, volume in reader)
