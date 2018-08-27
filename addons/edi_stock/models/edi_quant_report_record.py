"""EDI stock level report records"""

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include stock level report records"""

    _inherit = 'edi.document'

    quant_report_ids = fields.One2many(
        'edi.quant.report.record', 'doc_id',
        string="Stock Level Reports",
    )


class EdiQuantReportRecord(models.Model):
    """EDI stock level report record

    This is the base model for EDI stock level report records.  Each
    row represents a stock level that will be reported upon when the
    document is executed.

    The fields within each record represent the fields within the
    produced document, which may not exactly correspond to fields of
    the ``stock.quant`` model.  For example: the document may merge
    multiple quants into a single record, if the details of internal
    storage locations are not required.

    Derived models should implement either :meth:`~.record_values` or
    :meth:`~.prepare`.
    """

    _name = 'edi.quant.report.record'
    _inherit = 'edi.record'
    _description = "Stock Level Report"

    product_id = fields.Many2one('product.product', string="Product",
                                 required=True, readonly=True, index=True)
    qty = fields.Float(string="Quantity", required=True, readonly=True,
                       digits=dp.get_precision('Product Unit of Measure'))

    @api.model
    def record_values(self, quants):
        """Construct EDI record value dictionary

        Accepts a ``stock.quant`` recordset and constructs a
        corresponding value dictionary for an EDI stock level report
        record.
        """
        product = quants.mapped('product_id').ensure_one()
        return {
            'name': product.default_code,
            'product_id': product.id,
            'qty': sum(x.quantity for x in quants),
        }

    @api.model
    def prepare(self, doc, quantlist):
        """Prepare records"""
        for quants in quantlist:
            record_vals = self.record_values(quants)
            record_vals['doc_id'] = doc.id
            self.create(record_vals)
