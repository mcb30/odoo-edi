"""EDI stock move request records"""

import logging
from odoo import api, fields, models
from odoo.addons import decimal_precision as dp
from odoo.tools.translate import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include stock move request records"""

    _inherit = "edi.document"

    move_request_ids = fields.One2many(
        "edi.move.request.record",
        "doc_id",
        string="Stock Move Requests",
    )


class EdiMoveRequestRecord(models.Model):
    """EDI stock move request record

    This is the base model for EDI stock move request records.  Each
    row represents a line item within a stock transfer that will be
    created or updated when the document is executed.

    Derived models should implement :meth:`~.move_values`.
    """

    _name = "edi.move.request.record"
    _inherit = "edi.record"
    _description = "Stock Move Request"

    pick_key = fields.Char(
        string="Transfer key",
        required=True,
        readonly=True,
        index=True,
        edi_relates="pick_id.origin",
    )
    pick_id = fields.Many2one(
        "stock.picking",
        string="Transfer",
        domain=[("state", "!=", "cancel")],
        required=False,
        readonly=True,
        index=True,
    )
    tracker_key = fields.Char(
        string="Tracker Key",
        required=False,
        readonly=True,
        index=True,
        edi_relates="tracker_id.name",
    )
    tracker_id = fields.Many2one(
        "edi.move.tracker", string="Tracker", required=False, readonly=True, index=True
    )
    move_id = fields.Many2one("stock.move", "Move", required=False, readonly=True, index=True)
    product_key = fields.Char(
        string="Product Key",
        required=True,
        readonly=True,
        index=True,
        edi_relates="product_id.default_code",
    )
    product_id = fields.Many2one(
        "product.product", string="Product", required=False, readonly=True, index=True
    )
    qty = fields.Float(
        string="Quantity", readonly=True, required=True, digits="Product Unit of Measure"
    )

    def precache(self):
        """Precache associated records"""
        super().precache()
        self.mapped("product_id.product_tmpl_id.name")
        self.mapped("tracker_id.move_ids.name")

    def move_values(self):
        """Construct ``stock.move`` value dictionary

        We deliberately omit the ``stock.picking`` from the per-move
        value dictionary, since it is substantially more efficient to
        perform the association of moves to pickings as a bulk
        operation.
        """
        self.ensure_one()
        return {
            "name": self.name,
            "edi_tracker_id": self.tracker_id.id if self.tracker_id else False,
            "product_id": self.product_id.id,
            "product_uom_qty": self.qty,
            "product_uom_qty": self.qty,
            "product_uom": self.product_id.uom_id.id,
            "location_id": self.pick_id.location_id.id,
            "location_dest_id": self.pick_id.location_dest_id.id,
            "picking_type_id": self.pick_id.picking_type_id.id,
        }

    def existing_move(self):
        """Find corresponding existing move (if any)"""
        self.ensure_one()
        if not self.tracker_id:
            return self.env["stock.move"].browse()
        return self.tracker_id.move_ids.filtered(
            lambda x: x.state != "cancel"
            and x.product_id == self.product_id
            and x.picking_type_id == self.pick_id.picking_type_id
        )

    def execute(self):
        """Execute records"""
        # pylint: disable=too-many-locals
        super().execute()
        Move = self.env["stock.move"]
        Picking = self.env["stock.picking"]
        Product = self.env["product.product"]
        Template = self.env["product.template"]
        EdiMoveTracker = self.env["edi.move.tracker"]

        # Identify containing document
        doc = self.mapped("doc_id")

        # Process records in batches for efficiency
        cancel = Move.browse()
        for r, batch in self.batched(self.BATCH_SIZE):
            batch.precache()
            _logger.info(
                "%s executing %s %d-%d of %d", doc.name, self._name, r[0], r[-1], len(self)
            )

            # Create, update, or cancel moves
            for rec in batch:

                # Find existing move, if any
                move = rec.existing_move()
                if move:
                    if len(move) > 1:
                        raise UserError(_("Multiple existing moves for %s") % rec.name)
                    rec.move_id = move

                # Construct move value dictionary
                move_vals = rec.move_values()

                # Create, update, or cancel move as applicable
                if rec.move_id:
                    if rec.move_id.move_line_ids.filtered(lambda x: x.qty_done):
                        raise UserError(_("In-progress moves for %s") % rec.name)
                    if move_vals["product_uom_qty"]:
                        rec.move_id.write(move_vals)
                    else:
                        cancel += rec.move_id
                elif move_vals["product_uom_qty"]:
                    rec.move_id = Move.create(move_vals)

        # Associate moves to pickings.  Do this as a bulk operation to
        # avoid triggering updates on the picking for each new move.
        for pick, recs in self.groupby(lambda x: x.pick_id):
            recs.mapped("move_id").write({"picking_id": pick.id})

        # Cancel moves in bulk
        cancel._action_cancel()
