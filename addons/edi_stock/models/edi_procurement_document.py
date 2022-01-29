"""EDI procurement rule documents"""

from odoo import api, fields, models


class EdiProcurementDocument(models.AbstractModel):
    """EDI procurement rule document

    This is the base model for EDI procurement rule documents.  Each
    row represents a collection of EDI procurement rule records that,
    in turn, represent a procurement rule that will be created or
    updated when the document is executed.

    All input attachments are parsed to generate a list of potential
    EDI procurement rule records, represented in the form of a values
    dictionary that could be used to create the EDI procurement rule
    record.

    Procurement rule definitions typically change infrequently.  To
    minimise unnecessary duplication, any EDI procurement rule records
    that would not result in a new or modified ``procurement rule``
    record will be automatically elided from the document.

    Derived models should implement either :meth:`~.prepare` or
    :meth:`~.procurement_record_values`.
    """

    _name = "edi.procurement.document"
    _inherit = "edi.document.sync"
    _description = "Procurement Rules"

    @api.model
    def procurement_record_model(self, doc, supermodel="edi.procurement.record"):
        """Get EDI procurement rule record model class

        Subclasses should never need to override this method.
        """
        return self.record_model(doc, supermodel=supermodel)

    @api.model
    def procurement_record_values(self, _data):
        """Construct EDI procurement record value dictionaries

        Must return an iterable of dictionaries, each of which could
        passed to :meth:`~odoo.models.Model.create` in order to create
        an EDI procurement rule record.
        """
        return self.no_record_values()

    @api.model
    def prepare(self, doc):
        """Prepare document"""
        super().prepare(doc)
        self.procurement_record_model(doc).prepare(
            doc,
            (
                record_vals
                for _fname, data in doc.inputs()
                for record_vals in self.procurement_record_values(data)
            ),
        )
