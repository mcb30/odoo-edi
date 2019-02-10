"""EDI product records"""

from odoo import api, fields, models


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include EDI product records"""

    _inherit = 'edi.document'

    product_ids = fields.One2many('edi.product.record', 'doc_id',
                                  string="Products")
    inactive_product_ids = fields.One2many('edi.inactive.product.record',
                                           'doc_id', string="Inactive Products")


class EdiProductRecord(models.Model):
    """EDI product record

    This is the base model for EDI product records.  Each row
    represents a product that will be created or updated when the
    document is executed.

    The fields within each record represent the fields within the
    source document, which may not exactly correspond to fields of the
    ``product.product`` model.  For example: the source document may
    define a weight as an integer number of grams, whereas the
    ``product.product.weight`` field is defined as a floating point
    number of kilograms.

    Derived models should implement :meth:`~.target_values`.
    """

    _name = 'edi.product.record'
    _inherit = 'edi.record.sync.active'
    _description = "Product"

    _edi_sync_target = 'product_id'
    _edi_sync_via = 'default_code'

    product_id = fields.Many2one('product.product', string="Product",
                                 required=False, readonly=True, index=True,
                                 auto_join=True)
    description = fields.Char(string="Description", required=True,
                              readonly=True, default="Unknown")

    @api.model
    def target_values(self, record_vals):
        """Construct ``product.product`` field value dictionary"""
        product_vals = super().target_values(record_vals)
        product_vals.update({
            'name': record_vals['description'],
        })
        return product_vals


class EdiInactiveProductRecord(models.Model):
    """EDI inactive product record"""

    _name = 'edi.inactive.product.record'
    _inherit = 'edi.record.deactivator'
    _description = "Inactive Product"

    target_id = fields.Many2one('product.product', string="Product")
