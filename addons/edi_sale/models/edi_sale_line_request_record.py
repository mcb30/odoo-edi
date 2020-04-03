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
                       digits='Product Unit of Measure')


    def precache(self):
        """Precache associated records"""
        super().precache()
        self.mapped('product_id.product_tmpl_id.name')
        self.mapped('order_id.partner_id.name')


    def sale_line_values(self):
        """Construct ``sale.order.line`` value dictionary"""
        self.ensure_one()
        return {
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom': self.product_id.uom_id.id,
            'product_uom_qty': self.qty,
            'order_id': self.order_id.id,
        }


    def execute(self):
        """Execute records"""
        super().execute()
        SaleLine = self.env['sale.order.line']

        # Identify containing EDI document
        doc = self.mapped('doc_id')

        # Process records in batches for efficiency
        for r, batch in self.batched(self.BATCH_CREATE):

            _logger.info("%s creating %s %d-%d of %d",
                         doc.name, SaleLine._name, r[0], r[-1], len(self))

            # Create order lines
            with self.statistics() as stats:
                batch.precache()
                vals_list = list(self.add_edi_defaults(
                    SaleLine,
                    (rec.sale_line_values() for rec in batch)
                ))
                for rec, vals in zip(batch, vals_list):
                    rec.sale_line_id = SaleLine.create(vals)
                self.recompute()
            _logger.info("%s created %s %d-%d in %.2fs, %d excess queries",
                         doc.name, SaleLine._name, r[0], r[-1],
                         stats.elapsed, (stats.count - 2 * len(batch)))
