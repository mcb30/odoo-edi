"""EDI stock move report records"""

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include stock move report records"""

    _inherit = "edi.document"

    move_report_ids = fields.One2many(
        "edi.move.report.record",
        "doc_id",
        string="Stock Move Reports",
    )


class EdiMoveReportRecord(models.Model):
    """EDI stock move report record

    This is the base model for EDI stock move report records.  Each
    row represents a collection of line items within a stock transfer
    that will be reported upon when the document is executed.

    Derived models should implement either :meth:`~.record_values` or
    :meth:`~.prepare`.
    """

    _name = "edi.move.report.record"
    _inherit = "edi.record"
    _description = "Stock Move Report"

    move_ids = fields.Many2many(
        "stock.move", string="Moves", required=True, readonly=True, index=True
    )
    product_id = fields.Many2one(
        "product.product", string="Product", required=False, readonly=True, index=True
    )
    qty = fields.Float(
        string="Quantity", readonly=True, required=True, digits="Product Unit of Measure"
    )

    @api.model
    def record_values(self, moves):
        """Construct EDI record value dictionary

        Accepts a ``stock.move`` recordset and constructs a
        corresponding value dictionary for an EDI stock move report
        record.
        """
        product = moves.mapped("product_id").ensure_one()
        return {
            "name": moves.env.context.get("default_name", product.default_code),
            "move_ids": [(6, 0, moves.ids)],
            "product_id": product.id,
            "qty": sum(x.quantity_done for x in moves),
        }

    @api.model
    def prepare(self, doc, movelist):
        """Prepare records"""
        super().prepare(doc, (self.record_values(moves) for moves in movelist))
