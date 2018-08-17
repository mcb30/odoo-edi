"""EDI stock transfer request records"""

from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.exceptions import ValidationError


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

    Derived models should implement :meth:`~.pick_values`.
    """

    _name = 'edi.pick.request.record'
    _inherit = 'edi.record'
    _description = "Stock Transfer Request"

    pick_type_id = fields.Many2one('stock.picking.type', string="Type",
                                   required=True, readonly=True, index=True)
    pick_id = fields.Many2one('stock.picking', string="Transfer",
                              required=False, readonly=True, index=True)

    _sql_constraints = [('doc_name_uniq', 'unique (doc_id, name)',
                         "Each name may appear at most once per document")]

    @api.multi
    def get_not_started_picking(self):
        """ Gets a picking with origin equal to self.name and
            validates that the picking is not started
        """
        self.ensure_one()
        Picking = self.env['stock.picking']
        picking = Picking.search([
            ('origin', '=', self.name),
            ('picking_type_id', '=', self.pick_type_id.id),
            ('state', 'not in', ['done', 'cancel'])
        ])
        if picking.mapped('move_line_ids').filtered(lambda ml: ml.qty_done > 0):
            raise ValidationError(
                _('Picking %s already started.') %
                picking.mapped('origin'))

        return picking

    @api.multi
    def pick_values(self):
        """Construct ``stock.picking`` value dictionary"""
        self.ensure_one()
        pick_type = self.pick_type_id
        return {
            'origin': self.name,
            'picking_type_id': pick_type.id,
            'location_id': pick_type.default_location_src_id.id,
            'location_dest_id': pick_type.default_location_dest_id.id,
        }

    @api.multi
    def execute(self):
        """Execute records"""
        super().execute()
        Picking = self.env['stock.picking']
        for rec in self:
            picking = rec.get_not_started_picking()
            if not picking:
                pick_vals = rec.pick_values()
                picking = Picking.create(pick_vals)
            rec.pick_id = picking
