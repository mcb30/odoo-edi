"""EDI stock move request records"""

from itertools import groupby
from odoo import api, fields, models
from odoo.addons import decimal_precision as dp


class EdiMoveRequestRecord(models.Model):
    """EDI stock move request record

    This is the base model for EDI stock move request records.  Each
    row represents a line item within a stock transfer that will be
    created or updated when the document is executed.
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
                              readonly=True,
                              edi_relates='product_id.default_code')
    product_id = fields.Many2one('product.product', string="Product",
                                 required=False, readonly=True, index=True)
    qty = fields.Float(string="Quantity", readonly=True, required=True,
                       digits=dp.get_precision('Product Unit of Measure'))

    @api.multi
    def execute(self):
        """Execute records"""
        super().execute()
        Move = self.env['stock.move']

        # Create moves disassociated from any picking
        for rec in self:
            rec.move_id = Move.create({
                'name': rec.name,
                'product_id': rec.product_id.id,
                'product_uom_qty': rec.qty,
                'product_uom': rec.product_id.uom_id.id,
                'location_id': rec.pick_id.location_id.id,
                'location_dest_id': rec.pick_id.location_dest_id.id,
            })

        # Associate moves to pickings.  Do this as a bulk operation to
        # avoid triggering updates on the picking for each new move.
        for pick, moves in ((k, Move.union(*(x.move_id for x in v)))
                            for k, v in groupby(self.sorted('pick_id'),
                                                key=lambda x: x.pick_id)):
            moves.write({'picking_id': pick.id})
