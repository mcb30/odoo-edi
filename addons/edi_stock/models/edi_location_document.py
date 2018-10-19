"""EDI stock location documents"""

from odoo import api, fields, models


class EdiDocumentType(models.Model):
    """Extend ``edi.document.type`` to include associated stock locations"""

    _inherit = 'edi.document.type'

    location_ids = fields.Many2many('stock.location', string="Stock Locations")


class EdiLocationDocument(models.AbstractModel):
    """EDI location document

    This is the base model for EDI location documents.  Each row
    represents a collection of EDI location records that, in turn,
    represent a location that will be created or updated when the
    document is executed.

    All input attachments are parsed to generate a list of potential
    EDI location records, represented in the form of a values
    dictionary that could be used to create the EDI location record.

    Location definitions typically change infrequently.  To minimise
    unnecessary duplication, any EDI location records that would not
    result in a new or modified ``location.location`` record will be
    automatically elided from the document.

    Derived models should implement either :meth:`~.prepare` or
    :meth:`~.location_record_values`.
    """

    _name = 'edi.location.document'
    _inherit = 'edi.document.sync'
    _description = "Stock Locations"

    @api.model
    def location_record_model(self, doc, supermodel='edi.location.record'):
        """Get EDI location record model class

        Subclasses should never need to override this method.
        """
        return self.record_model(doc, supermodel=supermodel)

    @api.model
    def location_record_values(self, _data):
        """Construct EDI location record value dictionaries

        Must return an iterable of dictionaries, each of which could
        passed to :meth:`~odoo.models.Model.create` in order to create
        an EDI location record.
        """
        return self.no_record_values()

    @api.model
    def prepare(self, doc):
        """Prepare document"""
        super().prepare(doc)
        self.location_record_model(doc).prepare(doc, (
            record_vals
            for _fname, data in doc.inputs()
            for record_vals in self.location_record_values(data)
        ))
