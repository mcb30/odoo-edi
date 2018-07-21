"""EDI stock transfer request documents"""

from odoo import api, models


class EdiPickRequestDocument(models.AbstractModel):
    """EDI stock transfer request document

    This is the base model for EDI stock transfer request documents.
    Each row represents two collections of EDI records:

    - a collection of EDI stock transfer request records that, in
      turn, each represent a stock transfer that will be created or
      updated when the document is executed, and

    - a collection of EDI stock move request records that, in turn,
      each represent a line item within one of the above a stock
      transfers

    Derived models should implement :meth:`~.prepare`.
    """

    _name = 'edi.pick.request.document'
    _inherit = 'edi.document.model'
    _description = "Stock Transfer Requests"

    @api.model
    def pick_request_record_model(self, doc,
                                  supermodel='edi.pick.request.record'):
        """Get EDI stock transfer request record model class"""
        return self.record_model(doc, supermodel=supermodel)

    @api.model
    def move_request_record_model(self, doc,
                                  supermodel='edi.move.request.record'):
        """Get EDI stock move request record model class"""
        return self.record_model(doc, supermodel=supermodel)

    @api.model
    def prepare(self, doc):
        """Prepare document"""
        super().prepare(doc)
        # Ensure that at least one input file exists
        doc.inputs()
