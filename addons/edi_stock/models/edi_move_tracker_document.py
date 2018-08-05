"""EDI stock tracker documents"""

from odoo import api, models


class EdiMoveTrackerDocument(models.AbstractModel):
    """EDI stock move tracker document

    This is the base model for EDI stock move tracker documents.  Each
    row represents a collection of EDI stock move tracker records
    that, in turn, each represent an EDI stock move tracker that will
    be created or updated when the document is executed.

    All input attachments are parsed to generate a list of potential
    EDI stock move tracker records, represented in the form of a
    values dictionary that could be used to create the EDI stock move
    tracker record.

    Derived models should implement either :meth:`~.prepare` or
    :meth:`~.move_tracker_record_values`.
    """

    _name = 'edi.move.tracker.document'
    _inherit = 'edi.document.sync'
    _description = "Stock Move Trackers"

    @api.model
    def move_tracker_record_model(self, doc,
                                  supermodel='edi.move.tracker.record'):
        """Get EDI stock move tracker record model class"""
        return self.record_model(doc, supermodel=supermodel)

    @api.model
    def move_tracker_record_values(self, _data):
        """Construct EDI stock move tracker record value dictionaries

        Must return an iterable of dictionaries, each of which could
        passed to :meth:`~odoo.models.Model.create` in order to create
        an EDI stock move tracker record.
        """
        return ()

    @api.model
    def prepare(self, doc):
        """Prepare document"""
        super().prepare(doc)
        self.move_tracker_record_model(doc).prepare(doc, (
            record_vals
            for _fname, data in doc.inputs()
            for record_vals in self.move_tracker_record_values(data)
        ))
