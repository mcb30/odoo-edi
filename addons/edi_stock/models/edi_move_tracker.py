"""EDI stock move tracker"""

from odoo import api, fields, models


class StockMove(models.Model):
    """Extend ``stock.move`` to include the EDI stock move tracker"""

    _inherit = "stock.move"

    edi_tracker_id = fields.Many2one(
        "edi.move.tracker", string="EDI Tracker", required=False, index=True
    )


class EdiMoveTracker(models.Model):
    """EDI stock move tracker

    Represents a tracking identity used to associate stock move
    reports with the originating stock move request.
    """

    _name = "edi.move.tracker"
    _description = "Stock Move Tracker"

    name = fields.Char(string="Name", required=True, index=True)
    active = fields.Boolean(string="Active", default=True)
    move_ids = fields.One2many(
        comodel_name="stock.move", inverse_name="edi_tracker_id", string="Moves", auto_join=True
    )
    pick_ids = fields.One2many(
        comodel_name="stock.picking",
        string="Transfers",
        compute="_compute_pick_ids",
        compute_sudo=True,
    )

    # For searching use only
    pick_id = fields.Many2one(
        "stock.picking", string="Transfer", related="move_ids.picking_id", readonly=True
    )
    product_id = fields.Many2one(
        "product.product", string="Product", related="move_ids.product_id", readonly=True
    )

    @api.depends("move_ids", "move_ids.picking_id")
    def _compute_pick_ids(self):
        """Calculate associated stock transfers

        This method is required since Odoo cannot correctly handle a
        related field that traverses a Many2many followed by a
        Many2one.
        """
        self.mapped("move_ids.picking_id")
        for tracker in self:
            tracker.pick_ids = tracker.mapped("move_ids.picking_id")
