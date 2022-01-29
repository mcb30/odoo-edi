"""EDI stock route documents"""

from odoo import api, fields, models


class EdiRouteDocument(models.AbstractModel):
    """EDI route document

    This is the base model for EDI route documents.  Each row
    represents a collection of EDI route records that, in turn,
    represent a route that will be created or updated when the
    document is executed.

    All input attachments are parsed to generate a list of potential
    EDI route records, represented in the form of a values
    dictionary that could be used to create the EDI route record.

    Route definitions typically change infrequently.  To minimise
    unnecessary duplication, any EDI route records that would not
    result in a new or modified ``stock.location.route`` record will
    be automatically elided from the document.

    Derived models should implement either :meth:`~.prepare` or
    :meth:`~.route_record_values`.
    """

    _name = "edi.route.document"
    _inherit = "edi.document.sync"
    _description = "Stock Routes"

    @api.model
    def route_record_model(self, doc, supermodel="edi.route.record"):
        """Get EDI route record model class

        Subclasses should never need to override this method.
        """
        return self.record_model(doc, supermodel=supermodel)

    @api.model
    def route_record_values(self, _data):
        """Construct EDI route record value dictionaries

        Must return an iterable of dictionaries, each of which could
        passed to :meth:`~odoo.models.Model.create` in order to create
        an EDI route record.
        """
        return self.no_record_values()

    @api.model
    def prepare(self, doc):
        """Prepare document"""
        super().prepare(doc)
        self.route_record_model(doc).prepare(
            doc,
            (
                record_vals
                for _fname, data in doc.inputs()
                for record_vals in self.route_record_values(data)
            ),
        )
