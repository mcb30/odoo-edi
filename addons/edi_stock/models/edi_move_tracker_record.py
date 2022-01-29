"""EDI stock move tracker records"""

from odoo import api, fields, models


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include EDI stock move tracker records"""

    _inherit = "edi.document"

    move_tracker_ids = fields.One2many(
        "edi.move.tracker.record", "doc_id", string="Stock Move Trackers"
    )


class EdiMoveTrackerRecord(models.Model):
    """EDI stock move tracker record

    This is the base model for EDI stock move tracker records.  Each
    row represents an EDI stock move tracker that will be created or
    updated when the document is executed.

    Derived models should implement :meth:`~.target_values`.
    """

    _name = "edi.move.tracker.record"
    _inherit = "edi.record.sync.active"
    _description = "Stock Move Tracker"

    _edi_sync_target = "tracker_id"

    tracker_id = fields.Many2one(
        "edi.move.tracker",
        string="Tracker",
        required=False,
        readonly=True,
        index=True,
        auto_join=True,
    )
