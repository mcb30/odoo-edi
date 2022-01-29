"""EDI partner documents"""

from odoo import api, models


class EdiPartnerDocument(models.AbstractModel):
    """EDI partner document

    This is the base model for EDI partner documents.  Each row
    represents a collection of EDI partner records that, in turn,
    represent a partner that will be created or updated when the
    document is executed.

    All input attachments are parsed to generate a list of potential
    EDI partner records, represented in the form of a values
    dictionary that could be used to create the EDI partner record.

    Partner definitions typically change infrequently.  To minimise
    unnecessary duplication, any EDI partner records that would not
    result in a new or modified ``res.partner`` record will be
    automatically elided from the document.

    The ``res.partner.title`` field is unfortunately implemented as a
    separate relational model rather than a simple text string.  EDI
    partner documents may choose to inherit from both
    ``edi.partner.document`` and ``edi.partner.title.document`` and
    therefore use EDI partner title records to create any required
    partner titles.  A simpler (and almost certainly better) approach
    is to ignore the issue completely and rely upon the code in
    :meth:`edi.partner.record.missing_edi_relates_title_key` which
    will create any missing ``res.partner.title`` records
    automatically as needed.

    Derived models should implement either :meth:`~.prepare` or
    :meth:`~.partner_record_values`.
    """

    _name = "edi.partner.document"
    _inherit = "edi.document.sync"
    _description = "Partners"

    @api.model
    def partner_record_model(self, doc, supermodel="edi.partner.record"):
        """Get EDI partner record model class

        Subclasses should never need to override this method.
        """
        return self.record_model(doc, supermodel=supermodel)

    @api.model
    def partner_record_values(self, _data):
        """Construct EDI partner record value dictionaries

        Must return an iterable of dictionaries, each of which could
        passed to :meth:`~odoo.models.Model.create` in order to create
        an EDI partner record.
        """
        return self.no_record_values()

    @api.model
    def prepare(self, doc):
        """Prepare document"""
        super().prepare(doc)
        self.partner_record_model(doc).prepare(
            doc,
            (
                record_vals
                for _fname, data in doc.inputs()
                for record_vals in self.partner_record_values(data)
            ),
        )


class EdiPartnerTitleDocument(models.AbstractModel):
    """EDI partner title document

    This is the base model for EDI partner title documents.  Each row
    represents a collection of EDI partner title records that, in
    turn, represent a partner title that will be created or updated
    when the document is executed.

    All input attachments are parsed to generate a list of potential
    EDI partner title records, represented in the form of a values
    dictionary that could be used to create the EDI partner title
    record.

    Partner title definitions typically change infrequently.  To
    minimise unnecessary duplication, any EDI partner title records
    that would not result in a new or modified ``res.partner.title``
    record will be automatically elided from the document.

    Derived models should implement either :meth:`~.prepare` or
    :meth:`~.partner_title_record_values`.
    """

    _name = "edi.partner.title.document"
    _inherit = "edi.document.sync"
    _description = "Partner Titles"

    @api.model
    def partner_title_record_model(self, doc, supermodel="edi.partner.title.record"):
        """Get EDI partner title record model class

        Subclasses should never need to override this method.
        """
        return self.record_model(doc, supermodel=supermodel)

    @api.model
    def partner_title_record_values(self, _data):
        """Construct EDI partner title record value dictionaries

        Must return an iterable of dictionaries, each of which could
        passed to :meth:`~odoo.models.Model.create` in order to create
        an EDI partner title record.
        """
        return self.no_record_values()

    @api.model
    def prepare(self, doc):
        """Prepare document"""
        super().prepare(doc)
        self.partner_title_record_model(doc).prepare(
            doc,
            (
                record_vals
                for _fname, data in doc.inputs()
                for record_vals in self.partner_title_record_values(data)
            ),
        )
