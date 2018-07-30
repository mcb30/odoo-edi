"""EDI stock move request records"""

import logging
from itertools import groupby
from odoo import api, fields, models
from odoo.addons import decimal_precision as dp
from odoo.tools.translate import _
from odoo.addons.edi.tools import batched

_logger = logging.getLogger(__name__)


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
    move_id = fields.Many2one('stock.move', "Move", required=False,
                              readonly=True, index=True)
    product_key = fields.Char(string="Product Key", required=True,
                              readonly=True, index=True,
                              edi_relates='product_id.default_code')
    product_id = fields.Many2one('product.product', string="Product",
                                 required=False, readonly=True, index=True)
    qty = fields.Float(string="Quantity", readonly=True, required=True,
                       digits=dp.get_precision('Product Unit of Measure'))

    @api.multi
    def move_values(self):
        """Construct ``stock.move`` value dictionary"""
        self.ensure_one()
        return {
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom_qty': self.qty,
            'product_uom': self.product_id.uom_id.id,
            'location_id': self.pick_id.location_id.id,
            'location_dest_id': self.pick_id.location_dest_id.id,
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

        # Process records in batches for efficiency
        for r, batch in batched(self, self.BATCH_SIZE):

            _logger.info(_("%s executing %s %d-%d"),
                         doc.name, self._name, r[0], r[-1])

            # Cache all products, product templates, and picks for
            # this batch to reduce per-record database lookups
            recs = self.browse([x.id for x in batch])
            picks = Picking.browse(recs.mapped('pick_id.id'))
            picks.mapped('name')
            products = Product.browse(recs.mapped('product_id.id'))
            templates = Template.browse(products.mapped('product_tmpl_id.id'))
            templates.mapped('name')

            # Create moves disassociated from any picking
            for rec in recs:
                move_vals = rec.move_values()
                rec.move_id = Move.create(move_vals)

        # Associate moves to pickings.  Do this as a bulk operation to
        # avoid triggering updates on the picking for each new move.
        for pick, moves in ((k, Move.union(*(x.move_id for x in v)))
                            for k, v in groupby(self.sorted('pick_id'),
                                                key=lambda x: x.pick_id)):
            moves.write({'picking_id': pick.id})
