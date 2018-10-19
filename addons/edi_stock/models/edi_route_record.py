"""EDI stock route records"""

from odoo import api, fields, models


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include EDI stock route records"""

    _inherit = 'edi.document'

    route_ids = fields.One2many('edi.route.record', 'doc_id', string="Routes")
    inactive_route_ids = fields.One2many('edi.inactive.route.record', 'doc_id',
                                         string="Inactive Routes")


class EdiRouteRecord(models.Model):
    """EDI stock route record

    This is the base model for EDI stock route records.  Each row
    represents a stock route that will be created or updated when
    the document is executed.

    The fields within each record represent the fields within the
    source document, which may not exactly correspond to fields of the
    ``stock.location.route`` model.

    Derived models should implement :meth:`~.target_values`.
    """

    _name = 'edi.route.record'
    _inherit = 'edi.record.sync.active'
    _description = "Stock Route"

    _edi_sync_target = 'route_id'

    route_id = fields.Many2one('stock.location.route', string="Route",
                               required=False, readonly=True, index=True,
                               auto_join=True)

    @api.model
    def target_values(self, record_vals):
        """Construct ``stock.location.route`` field value dictionary"""
        route_vals = super().target_values(record_vals)
        return route_vals


class EdiInactiveRouteRecord(models.Model):
    """EDI inactive stock route record"""

    _name = 'edi.inactive.route.record'
    _inherit = 'edi.record.deactivator'
    _description = "Inactive Stock Route"

    target_id = fields.Many2one('stock.location.route', string="Route")
