"""EDI stock move request records"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    """Extend ``stock.move`` to include the EDI Stock Cancellation document"""

    _inherit = "stock.move"

    edi_stock_cancellation_doc_id = fields.Many2one(
        "edi.document",
        string="EDI Stock Cancellation Document",
        required=False,
        readonly=True,
        index=True,
    )


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include stock move cancellation records"""

    _inherit = "edi.document"

    move_cancellation_ids = fields.One2many(
        "edi.record.stock.cancellation",
        "doc_id",
        string="Move Cancellation Records",
    )


class EdiStockCancellationDocument(models.AbstractModel):
    """Stock Cancellation document model

    Stock Cancellation documents contain sets of moves
    (grouped by sale/pick partner & picking_type) which have been cancelled
    since the previous EDI export.
    """

    _name = "edi.document.stock.cancellation"
    _inherit = "edi.move.report.document"
    _description = "Stock Cancellations"

    _edi_move_report_via = "edi_stock_cancellation_doc_id"

    @api.model
    def move_report_domain(self, _doc):
        """
        Override to only include cancelled moves for picking types which have
        x_enable_pick_cancellation_email_notifs enabled.
        _edi_move_report_via functionality is kept to ensure moves are not reported on twice
        """
        StockPickingType = self.env["stock.picking.type"]
        picking_types_to_consider = StockPickingType.search(
            [("x_enable_pick_cancellation_email_notifs", "=", True)]
        )
        domain = [
            ("state", "=", "cancel"),
            (self._edi_move_report_via, "=", False),
            ("picking_id.picking_type_id", "in", picking_types_to_consider.ids),
        ]
        return domain

    @api.model
    def grouping_move_report_list(self, moves):
        """Group moves by sale & picking_type"""
        grouped_moves = []
        for _picking_type, moves_by_picking_type_and_partner in moves.groupby(
            lambda move: (move.picking_type_id, move.picking_id.partner_id)
        ):
            grouped_moves.append(moves_by_picking_type_and_partner)
        return grouped_moves

    @api.model
    def move_report_list(self, doc, moves):
        """
        Inherit to call a new grouping function
        which is extendable and return the grouped result, which will
        result in a cancellation record for each unique combination
        """
        res = super().move_report_list(doc, moves)
        return self.grouping_move_report_list(res)

    @api.model
    def execute(self, doc):
        """For each line, send an email using the template set on the line"""
        super().execute(doc)
        for record in doc.move_cancellation_ids:
            _logger.info(
                f"Sending email for Move Cancellation document: {doc.name}, Stock Cancellation: {record.name}"
            )
            email = record.email_template_id.send_mail(record.id, force_send=True)
            record.sent_email_id = email


class EdiStockCancellationRecord(models.Model):
    """Stock Cancellation record"""

    _name = "edi.record.stock.cancellation"
    _inherit = "edi.move.report.record"
    _description = "Stock Cancellation"

    order_reference = fields.Char(string="Order Reference", required=True, readonly=True)
    customer_id = fields.Many2one(
        string="Customer", comodel_name="res.partner", required=True, readonly=True
    )
    email_template_id = fields.Many2one(
        comodel_name="mail.template", string="Email Template", required=True, readonly=True
    )
    sent_email_id = fields.Many2one(comodel_name="mail.mail", string="Sent Email", readonly=True)

    @api.model
    def record_values(self, moves):
        """
        Override base method to no longer include product
        as we may have mixed product moves.
        Also include the new fields in the result.
        """
        # Cannot assume picking_type_id is set on the move
        mail_template = moves.mapped(
            "picking_id.picking_type_id.x_pick_cancellation_email_notif_template_id"
        )
        # Concept taken from super().record_values, just "," joined results for each move
        move_names = ",".join(
            [move.env.context.get("default_name", move.product_id.default_code) for move in moves]
        )
        values = {
            "name": move_names,
            "move_ids": [(6, 0, moves.ids)],
            "qty": sum(x.quantity_done for x in moves),
            "email_template_id": mail_template.id,
        }

        move_origins = moves.filtered(lambda move: move.picking_id.origin).mapped(
            "picking_id.origin"
        )
        # move_partner should be len(1) due to grouping in move_report_list()
        move_partner = moves.mapped("picking_id.partner_id")
        if not move_partner:
            raise ValidationError(
                _("Could not find partner for cancelled moves. Ensure partner is set for picks %s")
                % ",".join(moves.mapped("picking_id.name"))
            )
        values.update(
            {
                "order_reference": ",".join(move_origins) or "N/A",
                "customer_id": move_partner.id,
            }
        )
        return values
