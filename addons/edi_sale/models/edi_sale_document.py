"""EDI sale documents"""

from odoo import api, fields, models


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include sales

    Any EDI sale document model may extend
    :meth:`edi.document._compute_order_ids` to include its own
    associated ``sale.order`` records.
    """

    _inherit = 'edi.document'

    order_ids = fields.One2many('sale.order', string="Orders",
                                compute='_compute_order_ids')

    @api.multi
    def _compute_order_ids(self):
        """Calculate associated sale orders"""
        pass
