"""EDI stock level report documents"""

from odoo import api, models


class EdiQuantReportDocument(models.AbstractModel):
    """EDI stock level report document

    This is the base model for EDI stock level report documents.  Each
    row represents a collection of EDI stock level report records
    that, in turn, each represent a stock level that will be reported
    upon when the document is executed.

    Derived models should implement :meth:`~.quant_report_list` and
    :meth:`~.execute`, and may choose to implement
    :meth:`~.quant_domain`.
    """

    _name = 'edi.quant.report.document'
    _inherit = 'edi.document.model'
    _description = "Stock Level Reports"

    @api.model
    def quant_report_record_model(self, doc,
                                  supermodel='edi.quant.report.record'):
        """Get EDI stock level report record model class

        Subclasses should never need to override this method.
        """
        return self.record_model(doc, supermodel=supermodel)

    @api.model
    def quant_report_domain(self, doc):
        """Get stock quant search domain

        The default implementation returns all quants found within any
        associated stock location.
        """
        return [('location_id', 'child_of', doc.doc_type_id.location_ids.ids)]

    @api.model
    def quant_report_list(self, _doc, quants):
        """Get list of stock quants for which reports should be generated

        Returns an iterable of ``stock.quant`` recordsets.  Each
        recordset in the iterable will result in the creation of a
        single EDI stock level report record.

        Note that a recordset is itself an iterable of (singleton)
        recordsets.  This method may therefore return a single
        ``stock.quant`` recordset, in which case each individual
        ``stock.quant`` record will result in the creation of a
        separate EDI stock level report record.  The default
        implementation does exactly this.
        """
        return quants

    @api.model
    def prepare(self, doc):
        """Prepare document"""
        QuantReport = self.quant_report_record_model(doc)
        Quant = self.env['stock.quant']
        # Construct quant list
        quants = Quant.search(self.quant_report_domain(doc), order='id')
        quantlist = (x.with_prefetch(quants._prefetch_ids) for x in
                     self.quant_report_list(doc, quants))
        QuantReport.prepare(doc, quantlist)
