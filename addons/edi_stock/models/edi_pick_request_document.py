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

    Derived models should implement either :meth:`~.prepare` or
    :meth:`~.pick_request_record_values`.
    """

    _name = 'edi.pick.request.document'
    _inherit = 'edi.document.sync'
    _description = "Stock Transfer Requests"

    @api.model
    def pick_request_record_model(self, doc,
                                  supermodel='edi.pick.request.record'):
        """Get EDI stock transfer request record model class

        Subclasses should never need to override this method.
        """
        return self.record_model(doc, supermodel=supermodel)

    @api.model
    def move_request_record_model(self, doc,
                                  supermodel='edi.move.request.record'):
        """Get EDI stock move request record model class

        Subclasses should never need to override this method.
        """
        return self.record_model(doc, supermodel=supermodel)

    @api.model
    def pick_request_record_values(self, _data):
        """Construct EDI pick request record value dictionaries

        Must return an iterable of dictionaries, each of which could
        passed to :meth:`~odoo.models.Model.create` in order to create
        an EDI pick request record.
        """
        return self.no_record_values()

    @api.model
    def prepare(self, doc):
        """Prepare document"""
        super().prepare(doc)
        self.pick_request_record_model(doc).prepare(doc, (
            record_vals
            for _fname, data in doc.inputs()
            for record_vals in self.pick_request_record_values(data)
        ))
