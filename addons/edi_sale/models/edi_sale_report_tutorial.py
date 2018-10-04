"""EDI sale order report tutorial

This example shows the code required to implement a simple EDI sale
order report document format comprising a CSV file with a fixed list
of columns:

* Customer name
* Order reference
* Product reference
* Quantity
* Price subtotal
* Price total

The filenames will be constructed from the order reference.
"""

import csv
import io
from odoo import api, fields, models


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include sale order tutorial records"""

    _inherit = 'edi.document'

    sale_report_tutorial_ids = fields.One2many(
        'edi.sale.report.tutorial.record', 'doc_id',
        string="Sale Order Reports",
    )
    sale_line_report_tutorial_ids = fields.One2many(
        'edi.sale.line.report.tutorial.record', 'doc_id',
        string="Sale Order Line Move Reports",
    )

    @api.multi
    @api.depends('sale_report_tutorial_ids',
                 'sale_report_tutorial_ids.sale_id')
    def _compute_sale_ids(self):
        super()._compute_sale_ids()
        for doc in self:
            doc.sale_ids += doc.mapped('sale_report_tutorial_ids.sale_id')


class EdiSaleReportTutorialRecord(models.Model):
    """EDI sale order report tutorial record

    This subclass may be omitted if no extra functionality is required
    beyond that provided by the base ``edi.sale.report.record``.
    """

    _name = 'edi.sale.report.tutorial.record'
    _inherit = 'edi.sale.report.record'
    _description = "Sale Order Report"


class EdiSaleLineReportTutorialRecord(models.Model):
    """EDI sale order line report tutorial record

    This subclass may be omitted if no extra functionality is required
    beyond that required by the base ``edi.sale.line.report.record``.
    """

    _name = 'edi.sale.line.report.tutorial.record'
    _inherit = 'edi.sale.line.report.record'
    _description = "Sale Line Report"

    currency_id = fields.Many2one('res.currency', string="Currency",
                                  readonly=True, required=True)
    price_subtotal = fields.Monetary(string="Subtotal", required=True,
                                     readonly=True)
    price_total = fields.Monetary(string="Total", required=True, readonly=True)

    @api.model
    def record_values(self, lines):
        """Construct EDI record value dictionary"""
        vals = super().record_values(lines)
        currency = lines.mapped('currency_id').ensure_one()
        vals.update({
            'currency_id': currency.id,
            'price_subtotal': sum(lines.mapped('price_subtotal')),
            'price_total': sum(lines.mapped('price_total')),
        })
        return vals


class EdiSaleReportTutorialDocument(models.AbstractModel):
    """EDI sale order report tutorial document model"""

    _name = 'edi.sale.report.tutorial.document'
    _inherit = 'edi.sale.report.document'
    _description = "Tutorial sale order report CSV file"""

    @api.model
    def sale_line_report_list(self, _doc, lines):
        """Get sale order lines for which reports should be generated

        Sale order lines are grouped by by sale order and by product,
        and assigned a reporting name based on the order of appearance
        within the sale order.
        """
        return (
            product_lines.with_context(default_name='%04d' % index)
            for _order_id, order_lines in lines.groupby(lambda x: x.order_id.id)
            for index, (_product_id, product_lines) in enumerate(
                order_lines.groupby(lambda x: x.product_id.id)
            )
        )

    @api.model
    def execute(self, doc):
        """Execute document"""
        super().execute(doc)
        EdiSaleReportRecord = self.sale_report_record_model(doc)
        EdiSaleLineReportRecord = self.sale_line_report_record_model(doc)

        # Create output attachment for each picking
        sale_reports = EdiSaleReportRecord.search([('doc_id', '=', doc.id)])
        line_reports = EdiSaleLineReportRecord.search([('doc_id', '=', doc.id)])
        by_sale = lambda x: x.line_ids.mapped('order_id')
        for sale, recs in line_reports.groupby(by_sale, sort=False):
            # pylint: disable=cell-var-from-loop

            # Get corresponding sale report record
            sale_report = sale_reports.filtered(lambda x: x.sale_id == sale)
            sale_report.ensure_one()

            # Construct CSV file
            with io.StringIO() as output:
                writer = csv.writer(output, dialect='unix',
                                    quoting=csv.QUOTE_MINIMAL)
                for rec in recs:
                    writer.writerow([sale.partner_id.name, sale.name,
                                     rec.product_id.default_code, int(rec.qty),
                                     '%.2f' % rec.price_subtotal,
                                     '%.2f' % rec.price_total])
                data = output.getvalue().encode()

            # Create output attachment
            filename = '%s.csv' % ''.join(sale_report.name.split('/')[-2:])
            doc.output(filename, data)
