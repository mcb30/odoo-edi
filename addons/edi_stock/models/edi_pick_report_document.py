"""EDI stock transfer report documents"""

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class StockPicking(models.Model):
    """Extend ``stock.picking`` to include the EDI stock transfer report"""

    _inherit = 'stock.picking'

    edi_pick_report_id = fields.Many2one('edi.document',
                                         string="EDI Stock Transfer Report",
                                         required=False, readonly=True,
                                         index=True)


class EdiPickReportDocument(models.AbstractModel):
    """EDI stock transfer report document

    This is the base model for EDI stock transfer report documents.
    Each row represents two collections of EDI records:

    - a collection of EDI stock transfer report records that, in turn,
      each represent a stock transfer that will be reported upon when
      the document is executed, and

    - a collection of EDI stock move report records that, in turn,
      each represent a collection of line items within the above stock
      transfers

    Note that it is reasonably common for stock transfer report
    documents to aggregate multiple underlying ``stock.picking``
    and/or ``stock.move`` records.  For example: a stock transfer
    report document may specify the total quantity of each product
    dispatched, even if the stock was fetched from multiple warehouse
    locations.  For this reason, an EDI stock move report record may
    represent multiple stock transfer line items, and is not directly
    associated with a single EDI stock transfer report record.

    Derived models should implement :meth:`~.movelist` and
    :meth:`~.execute`.
    """

    _name = 'edi.pick.report.document'
    _inherit = 'edi.document.model'
    _description = "Stock Transfer Reports"

    @api.model
    def pick_report_record_model(self, doc,
                                 supermodel='edi.pick.report.record'):
        """Get EDI stock transfer report record model class"""
        return self.record_model(doc, supermodel=supermodel)

    @api.model
    def move_report_record_model(self, doc,
                                 supermodel='edi.move.report.record'):
        """Get EDI stock move report record model class"""
        return self.record_model(doc, supermodel=supermodel)

    @api.model
    def pickings(self, doc):
        """Get stock transfers for which reports should be generated

        The default implementation returns all completed stock
        transfers of any associated picking type for which a report
        has not yet been generated.
        """
        Picking = self.env['stock.picking']
        return Picking.search([
            ('edi_pick_report_id', '=', False),
            ('state', '=', 'done'),
            ('picking_type_id', 'in', doc.doc_type_id.pick_type_ids.ids),
        ])

    @api.model
    def movelist(self, _doc, moves):
        """Get stock moves for which reports should be generated

        Returns an iterable of ``stock.move`` recordsets.  Each
        recordset in the iterable will result in the creation of a
        single EDI stock move report record.

        Note that a recordset is itself an iterable of (singleton)
        recordsets.  This method may therefore return a single
        ``stock.move`` recordset, in which case each individual
        ``stock.move`` record will result in the creation of a
        separate EDI stock move report record.  The default
        implementation does exactly this.
        """
        return moves

    @api.model
    def prepare(self, doc):
        """Prepare document"""
        PickReport = self.pick_report_record_model(doc)
        MoveReport = self.move_report_record_model(doc)
        Move = self.env['stock.move']
        # Lock pickings to prevent concurrent report generation attempts
        picks = self.pickings(doc)
        picks.write({'edi_pick_report_id': False})
        # Construct move list
        moves = Move.search([('picking_id', 'in', picks.ids)])
        movelist = self.movelist(doc, moves)
        PickReport.prepare(doc, picks)
        MoveReport.prepare(doc, movelist)

    @api.model
    def execute(self, doc):
        """Execute document"""
        super().execute(doc)
        # Mark pickings as reported upon by this document
        doc.ensure_one()
        PickReport = self.pick_report_record_model(doc)
        pick_reports = PickReport.search([('doc_id', '=', doc.id)])
        picks = pick_reports.mapped('pick_id')
        reported_picks = picks.filtered(lambda x: x.edi_pick_report_id)
        if reported_picks:
            raise UserError(_("Report already generated for %s") %
                            ", ".join(reported_picks.mapped('name')))
        picks.write({'edi_pick_report_id': doc.id})
