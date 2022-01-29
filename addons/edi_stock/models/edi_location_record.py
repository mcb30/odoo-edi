"""EDI stock location records"""

from odoo import api, fields, models


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include EDI stock location records"""

    _inherit = "edi.document"

    location_ids = fields.One2many(
        "edi.location.record",
        "doc_id",
        string="Locations",
    )
    inactive_location_ids = fields.One2many(
        "edi.inactive.location.record",
        "doc_id",
        string="Inactive Locations",
    )


class EdiLocationRecord(models.Model):
    """EDI stock location record

    This is the base model for EDI stock location records.  Each row
    represents a stock location that will be created or updated when
    the document is executed.

    The fields within each record represent the fields within the
    source document, which may not exactly correspond to fields of the
    ``stock.location`` model.

    Derived models should implement :meth:`~.target_values`.
    """

    _name = "edi.location.record"
    _inherit = "edi.record.sync.active"
    _description = "Stock Location"

    _edi_sync_target = "location_id"
    _edi_sync_via = "barcode"

    location_id = fields.Many2one(
        "stock.location",
        string="Location",
        required=False,
        readonly=True,
        index=True,
        auto_join=True,
    )
    description = fields.Char(string="Description", required=True, readonly=True, default="Unknown")

    @api.model
    def target_values(self, record_vals):
        """Construct ``stock.location`` field value dictionary"""
        loc_vals = super().target_values(record_vals)
        loc_vals.update(
            {
                "name": record_vals["description"],
            }
        )
        return loc_vals


class EdiInactiveLocationRecord(models.Model):
    """EDI inactive stock location record"""

    _name = "edi.inactive.location.record"
    _inherit = "edi.record.deactivator"
    _description = "Inactive Stock Location"

    _edi_deactivator_name = "complete_name"

    target_id = fields.Many2one("stock.location", string="Location")
