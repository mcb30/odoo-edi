"""EDI stock move request records"""

import logging
from odoo import api, fields, models
from odoo.addons import decimal_precision as dp
from odoo.tools.translate import _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

MOVE_REQ_ACTIONS = [('C', 'Create'),
                    ('U', 'Update'),
                    ('D', 'Cancel'),
                    ]


class EdiMoveRequestRecord(models.Model):
    """EDI stock move request record

    This is the base model for EDI stock move request records.  Each
    row represents a line item within a stock transfer that will be
    created or updated when the document is executed.

    Derived models should implement :meth:`~.move_values`.
    """

    _name = 'edi.move.request.record'
    _inherit = 'edi.record'
    _description = "Stock Move Request"

    pick_request_id = fields.Many2one('edi.pick.request.record',
                                      string="Transfer Request",
                                      required=True, readonly=True,
                                      index=True)
    pick_id = fields.Many2one('stock.picking', string="Transfer",
                              related='pick_request_id.pick_id',
                              store=True, index=True)
    tracker_key = fields.Char(string="Tracker Key", required=False,
                              readonly=True, index=True,
                              edi_relates='tracker_id.name')
    tracker_id = fields.Many2one('edi.move.tracker', string="Tracker",
                                 required=False, readonly=True, index=True)
    move_id = fields.Many2one('stock.move', "Move", required=False,
                              readonly=True, index=True)
    product_key = fields.Char(string="Product Key", required=True,
                              readonly=True, index=True,
                              edi_relates='product_id.default_code')
    product_id = fields.Many2one('product.product', string="Product",
                                 required=False, readonly=True, index=True)
    qty = fields.Float(string="Quantity", readonly=True, required=True,
                       digits=dp.get_precision('Product Unit of Measure'))

    action = fields.Selection(selection=MOVE_REQ_ACTIONS, required=True,
                              default='C', index=True, readonly=True)

    @api.multi
    def move_values(self):
        """Construct ``stock.move`` value dictionary"""
        self.ensure_one()
        return {
            'name': self.name,
            'edi_tracker_id': self.tracker_id.id if self.tracker_id else False,
            'product_id': self.product_id.id,
            'product_uom_qty': self.qty,
            'product_uom': self.product_id.uom_id.id,
            'location_id': self.pick_id.location_id.id,
            'location_dest_id': self.pick_id.location_dest_id.id,
            'picking_type_id': self.pick_id.picking_type_id.id,
        }

    @api.multi
    def execute(self):
        """Execute records"""
        # pylint: disable=too-many-locals
        super().execute()
        Move = self.env['stock.move']
        Picking = self.env['stock.picking']
        Product = self.env['product.product']
        Template = self.env['product.template']

        # Identify containing document
        doc = self.mapped('doc_id')
        to_cancel = Move.browse()
        # Process records in batches for efficiency
        for r, batch in self.batched(self.BATCH_SIZE):

            _logger.info(_("%s executing %s %d-%d"),
                         doc.name, self._name, r[0], r[-1])

            # Cache all products, product templates, moves and picks for
            # this batch to reduce per-record database lookups
            picks = Picking.browse(batch.mapped('pick_id.id'))
            picks.mapped('name')
            products = Product.browse(batch.mapped('product_id.id'))
            templates = Template.browse(products.mapped('product_tmpl_id.id'))
            templates.mapped('name')
            # assume all picks will have the same picking_type_id
            moves = Move.search([('name', 'in', batch.mapped('name')),
                                 ('picking_type_id', '=',
                                  picks.mapped('picking_type_id').id),
                                 ('state', 'not in', ['done', 'cancel'])])
            moves.mapped('name')

            for rec in batch:
                move = moves.filtered(lambda m: m.name == rec.name)
                if rec.action == 'C':
                    if move:
                        raise ValidationError(
                            _('There is already an existing move with name %s' %
                              rec.name)
                        )
                    # Create moves disassociated from any picking
                    move_vals = rec.move_values()
                    rec.move_id = Move.create(move_vals)
                elif rec.action == 'U':
                    if not move:
                        raise ValidationError(
                            _('Cannot find move to update with name %s' %
                              rec.name)
                        )
                    rec.move_id = move
                    move_vals = rec.move_values()
                    move.update(move_vals)
                else:
                    if not move:
                        raise ValidationError(
                            _('Cannot find move to cancel with name %s' %
                              rec.name)
                        )
                    rec.move_id = move
                    to_cancel |= move

        # Associate moves to pickings.  Do this as a bulk operation to
        # avoid triggering updates on the picking for each new move.
        for pick_id, recs in self.groupby(lambda x: x.pick_id.id):
            recs.mapped('move_id').write({'picking_id': pick_id})

        # Cancel moves in bulk
        to_cancel._action_cancel()
