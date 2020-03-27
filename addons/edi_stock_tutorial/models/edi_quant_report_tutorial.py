"""EDI stock level report tutorial

This example shows the code required to implement a simple EDI stock
level report document format comprising a CSV file with a fixed list
of columns:

* Product code
* Quantity

The filenames will be constructed based on the date and time at which
the report is prepared.
"""

import csv
from datetime import datetime
import io
from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include stock level tutorial records"""

    _inherit = 'edi.document'

    quant_report_tutorial_ids = fields.One2many(
        'edi.quant.report.tutorial.record', 'doc_id',
        string="Stock Level Reports",
    )


class EdiQuantReportTutorialRecord(models.Model):
    """EDI stock level report tutorial record

    This subclass may be omitted if no extra functionality is required
    beyond that provided by the base ``edi.quant.report.record``.
    """

    _name = 'edi.quant.report.tutorial.record'
    _inherit = 'edi.quant.report.record'
    _description = "Stock Level Report"


class EdiQuantReportTutorialDocument(models.AbstractModel):
    """EDI stock level report tutorial document model"""

    _name = 'edi.quant.report.tutorial.document'
    _inherit = 'edi.quant.report.document'
    _description = "Tutorial stock level report CSV file"""

    @api.model
    def quant_report_list(self, _doc, quants):
        """Get quants for which reports should be generated

        Quants are grouped by product and assigned a reporting name
        based on the order within the report.
        """
        return (v.with_context(default_name='%05d' % i) for i, (k, v) in
                enumerate(quants.groupby(lambda x: x.product_id.default_code)))

    @api.model
    def execute(self, doc):
        """Execute document"""
        super().execute(doc)
        EdiQuantReportRecord = self.quant_report_record_model(doc)

        # Construct CSV file
        recs = EdiQuantReportRecord.search([('doc_id', '=', doc.id)])
        with io.StringIO() as output:
            writer = csv.writer(output, dialect='unix',
                                quoting=csv.QUOTE_MINIMAL)
            for rec in recs:
                writer.writerow([rec.product_id.default_code, int(rec.qty)])
            data = output.getvalue().encode()

        # Create output attachment
        filename = '%s%s.csv' % (doc.doc_type_id.sequence_id.prefix,
                                 doc.prepare_date.strftime('%Y%m%d%H%M%S'))
        doc.output(filename, data)
