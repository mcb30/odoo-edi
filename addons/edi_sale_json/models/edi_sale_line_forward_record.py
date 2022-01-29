"""EDI sale order line report records"""

from odoo import api, fields, models


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include sale order line report records"""

    _inherit = "edi.document"

    sale_line_forward_ids = fields.One2many(
        "edi.sale.line.forward.record",
        "doc_id",
        string="Sale Order Line Reports",
    )


class EdiSaleLineForwardRecord(models.Model):
    """EDI sale order line forward record"""

    _name = "edi.sale.line.forward.record"
    _inherit = "edi.sale.line.report.record"
    _description = "Sale Order Line Forward"

    sale_id = fields.Many2one(
        "sale.order",
        string="Order",
        required=True,
        readonly=True,
        index=True,
    )
    qty_delivered = fields.Float(required=False)

    @api.model
    def record_values(self, line):
        line.ensure_one()
        values = super().record_values(line)
        values.pop("qty_delivered")
        values.update({"name": line.name or values.get("name"), "sale_id": line.order_id.id})
        return values

    @api.model
    def prepare(self, doc, linelist):
        """Prepare records"""
        super().prepare(doc, (line for lines in linelist for line in lines))
