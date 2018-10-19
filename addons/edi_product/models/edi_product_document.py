"""EDI product documents"""

from odoo import api, models


class EdiProductDocument(models.AbstractModel):
    """EDI product document

    This is the base model for EDI product documents.  Each row
    represents a collection of EDI product records that, in turn,
    represent a product that will be created or updated when the
    document is executed.

    All input attachments are parsed to generate a list of potential
    EDI product records, represented in the form of a values
    dictionary that could be used to create the EDI product record.

    Product definitions typically change infrequently.  To minimise
    unnecessary duplication, any EDI product records that would not
    result in a new or modified ``product.product`` record will be
    automatically elided from the document.

    Derived models should implement either :meth:`~.prepare` or
    :meth:`~.product_record_values`.
    """

    _name = 'edi.product.document'
    _inherit = 'edi.document.sync'
    _description = "Products"

    @api.model
    def product_record_model(self, doc, supermodel='edi.product.record'):
        """Get EDI product record model class

        Subclasses should never need to override this method.
        """
        return self.record_model(doc, supermodel=supermodel)

    @api.model
    def product_record_values(self, _data):
        """Construct EDI product record value dictionaries

        Must return an iterable of dictionaries, each of which could
        passed to :meth:`~odoo.models.Model.create` in order to create
        an EDI product record.
        """
        return self.no_record_values()

    @api.model
    def prepare(self, doc):
        """Prepare document"""
        super().prepare(doc)
        self.product_record_model(doc).prepare(doc, (
            record_vals
            for _fname, data in doc.inputs()
            for record_vals in self.product_record_values(data)
        ))
