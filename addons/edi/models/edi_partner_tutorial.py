"""EDI partner tutorial

This example shows the code required to implement a simple EDI partner
document format comprising a CSV file with a fixed list of columns:

* Reference
* Title
* Full name
* E-mail address
"""

import csv
from odoo import api, fields, models


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include EDI partner tutorial records"""

    _inherit = 'edi.document'

    partner_tutorial_ids = fields.One2many('edi.partner.tutorial.record',
                                           'doc_id', string="Partners")


class EdiPartnerTutorialRecord(models.Model):
    """EDI partner tutorial record"""

    _name = 'edi.partner.tutorial.record'
    _inherit = 'edi.partner.record'
    _description = "Partner"

    email = fields.Char(string="Email", required=False, readonly=True,
                        index=True)

    @api.model
    def target_values(self, record_vals):
        partner_vals = super().target_values(record_vals)
        partner_vals.update({
            'email': record_vals['email'],
        })
        return partner_vals


class EdiPartnerTutorialDocument(models.AbstractModel):
    """EDI partner tutorial document model"""

    _name = 'edi.partner.tutorial.document'
    _inherit = 'edi.partner.document'
    _description = "Tutorial partner CSV file"

    @api.model
    def partner_record_values(self, data):
        reader = csv.reader(data.decode().splitlines())
        return ({
            'name': ref,
            'title_key': title,
            'full_name': name,
            'email': email,
        } for ref, title, name, email in reader)
