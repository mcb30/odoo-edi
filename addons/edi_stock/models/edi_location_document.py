"""EDI stock location documents"""

from odoo import fields, models


class EdiDocumentType(models.Model):
    """Extend ``edi.document.type`` to include associated stock locations"""

    _inherit = 'edi.document.type'

    location_ids = fields.Many2many('stock.location', string="Stock Locations")
