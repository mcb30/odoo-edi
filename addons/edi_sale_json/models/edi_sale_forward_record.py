"""EDI sale order report records"""

from odoo import api, fields, models


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include sale order report records"""

    _inherit = "edi.document"

    sale_report_ids = fields.One2many(
        "edi.sale.report.record",
        "doc_id",
        string="Sale Order Reports",
    )


class EdiSaleReportRecord(models.Model):
    """EDI sale order report record extends edi.sale.report with the fields required for the
    sale forward document
    """

    _name = "edi.sale.forward.record"
    _inherit = "edi.sale.report.record"
    _description = "Sale Order Forward"

    sale_ref = fields.Char(string="Order reference", required=True, readonly=True)
    partner_id = fields.Many2one("res.partner", required=True, readonly=True)

    @api.model
    def record_values(self, sale):
        """Construct EDI record value dictionary

        Accepts a ``sale.order`` record and constructs a
        corresponding value dictionary for an EDI sale order
        report record.
        """
        values = super().record_values(sale)
        values.update({"sale_ref": sale.origin or sale.name, "partner_id": sale.partner_id.id})
        return values
