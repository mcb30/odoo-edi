"""EDI procurement rule records"""

from odoo import api, fields, models


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include EDI procurement rule records"""

    _inherit = 'edi.document'

    procurement_ids = fields.One2many(
        'edi.procurement.record', 'doc_id', string="Procurement Rules",
    )
    inactive_procurement_ids = fields.One2many(
        'edi.inactive.procurement.record', 'doc_id',
        string="Inactive Procurement Rules",
    )


class EdiProcurementRecord(models.Model):
    """EDI procurement rule record

    This is the base model for EDI procurement rule records.  Each row
    represents a procurement rule that will be created or updated when
    the document is executed.

    The fields within each record represent the fields within the
    source document, which may not exactly correspond to fields of the
    ``procurement.rule`` model.

    Derived models should implement :meth:`~.target_values`.
    """

    _name = 'edi.procurement.record'
    _inherit = 'edi.record.sync.active'
    _description = "Procurement Rule"

    _edi_sync_target = 'rule_id'

    rule_id = fields.Many2one('procurement.rule', string="Procurement Rule",
                               required=False, readonly=True, index=True,
                               auto_join=True)
    route_key = fields.Char(string="Route Key", required=True, readonly=True,
                            index=True, edi_relates='route_id.name')
    route_id = fields.Many2one('stock.location.route', string="Route",
                               required=False, readonly=True, index=True)
    pick_type_id = fields.Many2one('stock.picking.type', string="Type",
                                   required=True, readonly=True, index=True)

    @api.model
    def target_values(self, record_vals):
        """Construct ``procurement.rule`` field value dictionary"""
        rule_vals = super().target_values(record_vals)
        rule_vals.update({
            'action': 'move',
            'route_id': record_vals['route_id'],
            'picking_type_id': record_vals['pick_type_id'],
        })
        return rule_vals


class EdiInactiveProcurementRecord(models.Model):
    """EDI inactive procurement rule record"""

    _name = 'edi.inactive.procurement.record'
    _inherit = 'edi.record.deactivator'
    _description = "Inactive Procurement Rule"

    target_id = fields.Many2one('procurement.rule', string="Rule")
