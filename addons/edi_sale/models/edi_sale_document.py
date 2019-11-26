"""EDI sale order documents"""

from odoo import api, fields, models


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include sale orders

    Any EDI sale order document model may extend
    :meth:`edi.document._compute_sale_ids` to include its own
    associated ``sale.order`` records.
    """

    _inherit = 'edi.document'

    sale_ids = fields.One2many('sale.order', string="Sale Orders",
                               compute='_compute_sale_ids')


    def _compute_sale_ids(self):
        """Calculate associated sale orders"""
        pass
