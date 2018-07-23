"""EDI minimum inventory rule records"""

from odoo import api, fields, models


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include EDI minimum inventory rule records"""

    _inherit = 'edi.document'

    orderpoint_ids = fields.One2many('edi.orderpoint.record', 'doc_id',
                                     string="Minimum Inventory Rules")


class EdiOrderpointRecord(models.Model):
    """EDI minimum inventory rule record

    This is the base model for EDI minimum inventory rule records.
    Each row represents a minimum inventory rule that will be created
    or updated when the document is executed.

    The fields within each record represent the fields within the
    source document, which may not exactly correspond to fields of the
    ``stock.warehouse.orderpoint`` model.  For example: the source
    document may define a lead time in weeks, whereas the
    ``stock.warehouse.orderpoint`` field is defined as a number of
    days.

    Derived models should implement :meth:`~.target_values`.
    """

    _name = 'edi.orderpoint.record'
    _inherit = 'edi.record.sync'
    _description = "Minimum Inventory Rule"

    _edi_sync_target = 'orderpoint_id'

    orderpoint_id = fields.Many2one('stock.warehouse.orderpoint',
                                    string="Minimum Inventory Rule",
                                    required=False, readonly=True, index=True,
                                    auto_join=True)
    product_key = fields.Char(string="Product Key", required=True,
                              readonly=True,
                              edi_relates='product_id.default_code')
    product_id = fields.Many2one('product.product', string="Product",
                                 required=False, readonly=True, index=True)
    location_key = fields.Char(string="Location Key", required=True,
                               readonly=True, edi_relates='location_id.name')
    location_id = fields.Many2one('stock.location', string="Location",
                                  required=False, readonly=True, index=True)
    product_min_qty = fields.Float(string="Minimum Quantity", required=True,
                                   readonly=True)
    product_max_qty = fields.Float(string="Maximum Quantity", required=True,
                                   readonly=True)

    @api.model
    def target_values(self, record_vals):
        """Construct ``stock.warehouse.orderpoint`` field value dictionary"""
        orderpoint_vals = super().target_values(record_vals)
        orderpoint_vals.update({
            'product_min_qty': record_vals['product_min_qty'],
            'product_max_qty': record_vals['product_max_qty'],
            'active': True,
        })
        return orderpoint_vals
