"""EDI sale line request records"""

import logging
from odoo import api, fields, models
from odoo.addons import decimal_precision as dp

_logger = logging.getLogger(__name__)


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include sale line request records"""

    _inherit = 'edi.document'

    sale_line_request_ids = fields.One2many(
        'edi.sale.line.request.record', 'doc_id',
        string="Sale Line Requests",
    )


class EdiSaleLineRequestRecord(models.Model):
    """EDI sale line request record

    This is the base model for EDI sale line request records.  Each
    row represents a line item within a sale that will be created or
    updated when the document is executed.

    Derived models should implement :meth:`~.sale_line_values`.
    """

    _name = 'edi.sale.line.request.record'
    _inherit = 'edi.record'
    _description = "Sale Line Request"

    sale_line_id = fields.Many2one('sale.order.line', "Line", required=False,
                                   readonly=True, index=True)
    order_key = fields.Char(string="Order Key", required=True,
                            readonly=True, index=True,
                            edi_relates='order_id.origin')
    order_id = fields.Many2one('sale.order', string="Order",
                               required=False, readonly=True, index=True)
    product_key = fields.Char(string="Product Key", required=True,
                              readonly=True, index=True,
                              edi_relates='product_id.default_code')
    product_id = fields.Many2one('product.product', string="Product",
                                 required=False, readonly=True, index=True)
    qty = fields.Float(string="Quantity", readonly=True, required=True,
                       digits=dp.get_precision('Product Unit of Measure'))

    @api.multi
    def sale_line_values(self):
        """Construct ``sale.order.line`` value dictionary"""
        self.ensure_one()
        return {
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom_qty': self.qty,
            'order_id': self.order_id.id,
        }

    @api.multi
    def execute(self):
        """Execute records"""
        super().execute()
        SaleLine = self.env['sale.order.line']
        Sale = self.env['sale.order']
        Product = self.env['product.product']
        Template = self.env['product.template']

        # Identify containing EDI document
        doc = self.mapped('doc_id')

        # Process records in batches for efficiency
        for r, batch in self.batched(self.BATCH_SIZE):

            _logger.info("%s executing %s %d-%d of %d",
                         doc.name, self._name, r[0], r[-1], len(self))

            # Cache related records for this batch to reduce
            # per-record database lookups
            sales = Sale.browse(batch.mapped('order_id.id'))
            sales.mapped('name')
            products = Product.browse(batch.mapped('product_id.id'))
            templates = Template.browse(products.mapped('product_tmpl_id.id'))
            templates.mapped('name')

            # Create order lines
            for rec in batch:
                line_vals = rec.sale_line_values()
                rec.sale_line_id = SaleLine.create(line_vals)
