"""EDI sale order line report records"""

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp


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

    line_ids = fields.Many2many('sale.order.line', string="Lines",
                                required=True, readonly=True, index=True)
    product_id = fields.Many2one('product.product', string="Product",
                                 required=False, readonly=True, index=True)
    qty = fields.Float(string="Quantity", readonly=True, required=True,
                       digits=dp.get_precision('Product Unit of Measure'))

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
            'qty': sum(x.quantity_delivered for x in lines),
        }

    @api.model
    def prepare(self, doc, linelist):
        """Prepare records"""
        for lines in linelist:
            record_vals = self.record_values(lines)
            record_vals['doc_id'] = doc.id
            self.create(record_vals)
