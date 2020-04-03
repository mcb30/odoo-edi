"""EDI sale order line report records"""

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include sale order line report records"""

    _inherit = 'edi.document'

    sale_line_report_ids = fields.One2many(
        'edi.sale.line.report.record', 'doc_id',
        string="Sale Order Line Reports",
    )


class EdiSaleLineReportRecord(models.Model):
    """EDI sale order line report record

    This is the base model for EDI sale order line report records.
    Each row represents a collection of line items within a sale order
    that will be reported upon when the document is executed.

    Derived models should implement either :meth:`~.record_values` or
    :meth:`~.prepare`.
    """

    _name = 'edi.sale.line.report.record'
    _inherit = 'edi.record'
    _description = "Sale Order Line Report"

    line_ids = fields.Many2many(
        'sale.order.line', string="Lines",
        required=True, readonly=True, index=True,
    )
    product_id = fields.Many2one(
        'product.product', string="Product",
        required=False, readonly=True, index=True,
    )
    qty_ordered = fields.Float(
        string="Ordered", readonly=True, required=True,
        digits='Product Unit of Measure',
    )
    qty_delivered = fields.Float(
        string="Delivered", readonly=True, required=True,
        digits='Product Unit of Measure',
    )

    @api.model
    def record_values(self, lines):
        """Construct EDI record value dictionary

        Accepts a ``sale.order.line`` recordset and constructs a
        corresponding value dictionary for an EDI sale order line
        report record.
        """
        product = lines.mapped('product_id').ensure_one()
        return {
            'name': lines.env.context.get('default_name', product.default_code),
            'line_ids': [(6, 0, lines.ids)],
            'product_id': product.id,
            'qty_ordered': sum(x.product_uom_qty for x in lines),
            'qty_delivered': sum(x.qty_delivered for x in lines),
        }

    @api.model
    def prepare(self, doc, linelist):
        """Prepare records"""
        super().prepare(doc, (self.record_values(lines) for lines in linelist))
