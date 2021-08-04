"""EDI stock move report documents"""

from odoo import api, fields, models, tools
from odoo.exceptions import UserError
from odoo.tools.translate import _


class StockMove(models.Model):
    """Extend ``stock.move`` to include the EDI stock move report"""

    _inherit = "stock.move"

    edi_move_report_id = fields.Many2one(
        "edi.document",
        string="EDI Stock Move Report",
        required=False,
        readonly=True,
        index=True,
    )


class EdiMoveReportDocument(models.AbstractModel):
    """EDI stock move report document

    This is the base model for EDI move report documents.
    Each row represents a collections of EDI stock move report records

    Derived models should implement :meth:`~.move_report_list` and
    :meth:`~.execute`, and may choose to implement
    :meth:`~.move_report_domain`.
    """

    _name = "edi.move.report.document"
    _inherit = "edi.document.model"
    _description = "Stock Move Reports"

    _edi_move_report_via = "edi_move_report_id"
    """Report record field

    This field is used to record the EDI document used to report upon
    a ``stock.move``.  It may be overridden if there is a need to
    report more than once upon a single ``stock.move`` record.
    """

    @api.model_cr
    def init(self):
        """Create index for :meth:`~.move_report_domain`

        This method follows the logic of :meth:`~.move_report_domain`, which
        returns a domain with either two or three clauses depending on the
        value of `~._edi_move_report_via`. To complicate things,
        `~._edi_move_report_via` is allowed to be overridden in models
        inheriting from this one. This method gets called for each derived
        model and creates the appropriate index for each one.
        """
        super(EdiMoveReportDocument, self).init()

        Move = self.env["stock.move"]

        if self._edi_move_report_via is not None:
            tools.create_index(
                self._cr,
                "stock_move_state_picking_type_id_%s_index" % (self._edi_move_report_via,),
                Move._table,
                ["state", "picking_type_id", self._edi_move_report_via],
            )
        else:
            tools.create_index(
                self._cr,
                "stock_move_state_picking_type_id_index",
                Move._table,
                ["state", "picking_type_id"],
            )

    @api.model
    def move_report_record_model(self, doc, supermodel="edi.move.report.record"):
        """Get EDI stock move report record model class

        Subclasses should never need to override this method.
        """
        return self.record_model(doc, supermodel=supermodel)

    @api.model
    def move_report_domain(self, doc):
        """Get stock move search domain

        The default implementation returns all completed moves
        associated with the specified picking types for which a report
        has not yet been generated
        """
        domain = [
            ("picking_type_id", "in", doc.doc_type_id.pick_type_ids.ids),
            ("state", "=", "done"),
        ]
        if self._edi_move_report_via is not None:
            domain.append((self._edi_move_report_via, "=", False))
        return domain

    @api.model
    def move_report_list(self, _doc, moves):
        """Get list of stock moves for which reports should be generated

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
        MoveReport = self.move_report_record_model(doc)
        Move = self.env["stock.move"]
        # Lock moves to prevent concurrent report generation attempts
        moves = Move.search(self.move_report_domain(doc), order="id")
        if self._edi_move_report_via is not None:
            moves.write({self._edi_move_report_via: False})
        movelist = (
            move.with_prefetch(moves._prefetch) for move in self.move_report_list(doc, moves)
        )
        # Prepare records
        MoveReport.prepare(doc, movelist)

    @api.model
    def execute(self, doc):
        """Execute document"""
        super().execute(doc)
        # Mark moves as reported upon by this document
        doc.ensure_one()
        MoveReport = self.move_report_record_model(doc)
        move_reports = MoveReport.search([("doc_id", "=", doc.id)])
        moves = move_reports.mapped("move_ids")
        if self._edi_move_report_via is not None:
            reported_moves = moves.filtered(self._edi_move_report_via)
            if reported_moves:
                raise UserError(
                    _("Report already generated for %s") % ", ".join(reported_moves.mapped("name"))
                )
            moves.write({self._edi_move_report_via: doc.id})
