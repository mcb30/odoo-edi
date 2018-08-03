"""EDI stock transfer report tutorial

This example shows the code required to implement a simple EDI pick
report document format comprising a CSV file with a fixed list of
columns:

* Product code
* Quantity

The filenames will be constructed based on the sequence prefix defined
for the picking types.  For example: a picking type with a prefix
"WH/OUT/" will result in a filename starting with "OUT".
"""

import csv
import io
from itertools import groupby
from odoo import api, fields, models


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include stock transfer tutorial records"""

    _inherit = 'edi.document'

    pick_report_tutorial_ids = fields.One2many(
        'edi.pick.report.tutorial.record', 'doc_id',
        string="Stock Transfer Reports",
    )
    move_report_tutorial_ids = fields.One2many(
        'edi.move.report.tutorial.record', 'doc_id',
        string="Stock Move Reports",
    )

    @api.multi
    @api.depends('pick_report_tutorial_ids',
                 'pick_report_tutorial_ids.pick_id')
    def _compute_pick_ids(self):
        super()._compute_pick_ids()
        for doc in self:
            doc.pick_ids += doc.mapped('pick_report_tutorial_ids.pick_id')


class EdiPickReportTutorialRecord(models.Model):
    """EDI stock transfer report tutorial record

    This subclass may be omitted if no extra functionality is required
    beyond that provided by the base ``edi.pick.report.record``.
    """

    _name = 'edi.pick.report.tutorial.record'
    _inherit = 'edi.pick.report.record'
    _description = "Stock Transfer Report"


class EdiMoveReportTutorialRecord(models.Model):
    """EDI stock move report tutorial record

    This subclass may be omitted if no extra functionality is required
    beyond that required by the base ``edi.move.report.record``.
    """

    _name = 'edi.move.report.tutorial.record'
    _inherit = 'edi.move.report.record'
    _description = "Stock Move Report"


class EdiPickReportTutorialDocument(models.AbstractModel):
    """EDI stock transfer report tutorial document model"""

    _name = 'edi.pick.report.tutorial.document'
    _inherit = 'edi.pick.report.document'
    _description = "Tutorial stock transfer report CSV file"""

    @api.model
    def movelist(self, _doc, moves):
        """Get moves for which reports should be generated

        Moves are grouped by stock transfer and by product, and
        assigned a reporting name based on the order within the stock
        transfer.
        """
        Move = self.env['stock.move']
        by_pick = lambda x: x.picking_id
        by_product = lambda x: x.product_id
        return (
            Move.union(*product_moves).with_context(
                default_name='%04d' % index
            )
            for _pick, pick_moves in (
                (k, Move.union(*v)) for k, v in groupby(
                    moves.sorted(key=by_pick), key=by_pick
                )
            )
            for index, (_product, product_moves) in enumerate(
                (k, Move.union(*v)) for k, v in groupby(
                    pick_moves.sorted(key=by_product), key=by_product
                )
            )
        )

    @api.model
    def prepare(self, doc):
        """Prepare document"""
        super().prepare(doc)
        EdiPickReportRecord = self.pick_report_record_model(doc)
        EdiMoveReportRecord = self.move_report_record_model(doc)

        # Create output attachment for each picking
        pick_reports = EdiPickReportRecord.search([('doc_id', '=', doc.id)])
        move_reports = EdiMoveReportRecord.search([('doc_id', '=', doc.id)])
        by_pick = lambda x: x.move_ids.mapped('picking_id')
        for pick, recs in groupby(move_reports, key=by_pick):
            # pylint: disable=cell-var-from-loop

            # Get corresponding pick report record
            pick_report = pick_reports.filtered(lambda x: x.pick_id == pick)
            pick_report.ensure_one()

            # Construct CSV file
            with io.StringIO() as output:
                writer = csv.writer(output, dialect='unix',
                                    quoting=csv.QUOTE_MINIMAL)
                for rec in recs:
                    writer.writerow([rec.product_id.default_code, int(rec.qty)])
                data = output.getvalue().encode()

            # Create output attachment
            filename = '%s.csv' % ''.join(pick_report.name.split('/')[-2:])
            doc.output(filename, data)
