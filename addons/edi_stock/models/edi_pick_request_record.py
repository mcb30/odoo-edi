"""EDI stock transfer request records"""

from odoo import api, fields, models


class EdiPickRequestRecord(models.Model):
    """EDI stock transfer request record

    This is the base model for EDI stock transfer request records.
    Each row represents a stock transfer that will be created or
    updated when the document is executed.

    The fields within each record represent the fields within the
    source document, which may not exactly correspond to fields of the
    ``stock.picking`` model.  For example: the source document may
    define a priority level which could be converted to a stock
    transfer due date based on some hardcoded business rules.

    Derived models should implement :meth:`~.target_values`.
    """

    _name = 'edi.pick.request.record'
    _inherit = 'edi.record.sync'
    _description = "Stock Transfer Request"

    _edi_sync_target = 'pick_id'
    _edi_sync_via = 'origin'

    pick_type_id = fields.Many2one('stock.picking.type', string="Type",
                                   required=True, readonly=True, index=True)
    pick_id = fields.Many2one('stock.picking', string="Transfer",
                              required=False, readonly=True, index=True)

    _sql_constraints = [('doc_name_uniq', 'unique (doc_id, name)',
                         "Each name may appear at most once per document")]

    @api.model
    def target_values(self, record_vals):
        """Construct ``stock.picking`` value dictionary"""
        pick_vals = super().target_values(record_vals)
        PickingType = self.env['stock.picking.type']
        pick_type = PickingType.browse(record_vals['pick_type_id'])
        pick_vals.update({
            'origin': record_vals['name'],
            'picking_type_id': pick_type.id,
            'location_id': pick_type.default_location_src_id.id,
            'location_dest_id': pick_type.default_location_dest_id.id,
        })
        return pick_vals
