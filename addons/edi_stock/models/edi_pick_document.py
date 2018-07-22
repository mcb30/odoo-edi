"""EDI stock transfer documents"""

from odoo import api, fields, models


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include stock transfers

    Any EDI stock transfer document model may extend
    :meth:`edi.document._compute_pick_ids` to include its own
    associated ``stock.picking`` records.
    """

    _inherit = 'edi.document'

    pick_ids = fields.One2many('stock.picking', string="Stock Transfers",
                               compute='_compute_pick_ids')

    @api.multi
    def _compute_pick_ids(self):
        """Calculate associated stock transfers"""
        pass
