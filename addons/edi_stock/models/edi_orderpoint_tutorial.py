"""EDI minimum inventory rule tutorial

This example shows the code required to implement a simple EDI minimum
inventory rule document format comprising a CSV file with a fixed list
of columns:

* Product code
* Location name
* Minimum quantity
* Maximum quantity
* Lead time (in weeks)
"""

import csv
from odoo import api, fields, models


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include EDI inventory rule tutorial records"""

    _inherit = 'edi.document'

    orderpoint_tutorial_ids = fields.One2many('edi.orderpoint.tutorial.record',
                                              'doc_id',
                                              string="Minimum Inventory Rules")


class EdiOrderpointTutorialRecord(models.Model):
    """EDI minimum inventory rule tutorial record"""

    _name = 'edi.orderpoint.tutorial.record'
    _inherit = 'edi.orderpoint.record'
    _description = "Minimum Inventory Rule"

    lead_weeks = fields.Integer(string="Lead Time", required=True,
                                readonly=True, help="Lead Time (in weeks)")

    @api.model
    def target_values(self, record_vals):
        orderpoint_vals = super().target_values(record_vals)
        orderpoint_vals.update({
            'lead_days': (record_vals['lead_weeks'] * 7),
        })
        return orderpoint_vals


class EdiOrderpointTutorialDocument(models.AbstractModel):
    """EDI minimum inventory rule tutorial document model"""

    _name = 'edi.orderpoint.tutorial.document'
    _inherit = 'edi.orderpoint.document'
    _description = "Tutorial mininum inventory rule CSV file"

    @api.model
    def orderpoint_record_values(self, data):
        reader = csv.reader(data.decode().splitlines())
        return ({
            'name': '%s@%s' % (product, location),
            'product_key': product,
            'location_key': location,
            'product_min_qty': float(minimum),
            'product_max_qty': float(maximum),
            'lead_weeks': int(lead),
        } for product, location, minimum, maximum, lead in reader)
