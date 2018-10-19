"""EDI minimum inventory rule documents"""

from odoo import api, models


class EdiOrderpointDocument(models.AbstractModel):
    """EDI minimum inventory rule document

    This is the base model for EDI minimum inventory rule documents.
    Each row represents a collection of EDI minimum inventory rule
    records that, in turn, each represent a minimum inventory rule
    that will be created or updated when the document is executed.

    All input attachments are parsed to generate a list of potential
    EDI minimum inventory rule records, represented in the form of a
    values dictionary that could be used to create the EDI minimum
    inventory rule record.

    Minimum inventory rule definitions typically change infrequently.
    To minimise unnecessary duplication, any EDI minimum inventory
    rule records that would not result in a new or modified
    ``stock.warehouse.orderpoint`` record will be automatically elided
    from the document.

    Derived models should implement either :meth:`~.prepare` or
    :meth:`~.orderpoint_record_values`.
    """

    _name = 'edi.orderpoint.document'
    _inherit = 'edi.document.sync'
    _description = "Minimum Inventory Rules"

    @api.model
    def orderpoint_record_model(self, doc, supermodel='edi.orderpoint.record'):
        """Get EDI minimum inventory rule record model class

        Subclasses should never need to override this method.
        """
        return self.record_model(doc, supermodel=supermodel)

    @api.model
    def orderpoint_record_values(self, _data):
        """Construct EDI minimum inventory rule record value dictionaries

        Must return an iterable of dictionaries, each of which could
        passed to :meth:`~odoo.models.Model.create` in order to create
        an EDI minimum inventory rule record.
        """
        return self.no_record_values()

    @api.model
    def prepare(self, doc):
        """Prepare document"""
        super().prepare(doc)
        self.orderpoint_record_model(doc).prepare(doc, (
            record_vals
            for _fname, data in doc.inputs()
            for record_vals in self.orderpoint_record_values(data)
        ))
