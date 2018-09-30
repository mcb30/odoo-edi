"""EDI product records"""

from odoo import api, fields, models


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
    def targets_by_key(self, vlist):
        """Construct lookup cache of target records indexed by key field"""
        products_by_key = super().targets_by_key(vlist)
        # Cache product templates to minimise subsequent database lookups
        Product = self.browse()[self._edi_sync_target].with_context(
            active_test=False
        )
        Template = Product.product_tmpl_id
        products = Product.browse([x.id for x in products_by_key.values()])
        templates = Template.browse(products.mapped('product_tmpl_id.id'))
        templates.mapped('name')
        return products_by_key

    @api.model
    def target_values(self, record_vals):
        """Construct ``product.product`` field value dictionary"""
        product_vals = super().target_values(record_vals)
        product_vals.update({
            'name': record_vals['description'],
        })
        return product_vals
