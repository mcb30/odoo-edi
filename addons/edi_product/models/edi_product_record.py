"""EDI product records"""

import logging
from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.addons.edi.tools import batched

_logger = logging.getLogger(__name__)


class EdiProductRecord(models.AbstractModel):
    """An EDI product record

    This is the base model for EDI product records.  Each row
    represents a product that will be created or updated when the
    document is executed.

    The fields within each record represent the fields within the
    source document, which may not exactly correspond to fields of the
    ``product.product`` model.  For example: the source document may
    define a weight as an integer number of grams, whereas the
    ``product.product.weight`` field is defined as a floating point
    number of kilograms.

    Derived models should implement :meth:`~._product_values` and
    :meth:`~._product_changed`.
    """

    BATCH_SIZE = 1000
    """Batch size for creating or updating products

    This is used primarily to restrict the number of log messages
    produced during document execution.
    """

    KEY_FIELD = 'default_code'
    """Lookup key field

    This specifies the field of ``product.product`` that is used to
    identify the existing product (if any) corresponding to an EDI
    product record.  Defaults to ``product.product.default_code``.

    The lookup value will be taken from the ``name`` field of the EDI
    product record.
    """

    _name = 'edi.product.record'
    _inherit = 'edi.record'
    _description = "Product"

    product_id = fields.Many2one('product.product', string="Product",
                                 required=False, readonly=True, index=True,
                                 auto_join=True)
    description = fields.Char(string="Description", required=True,
                              readonly=True, default="Unknown")

    @api.multi
    def _product_values(self):
        """Construct ``product.product`` field value dictionary

        Must return a dictionary that can be passed to
        :meth:`~odoo.models.Model.create` or
        :meth:`~odoo.models.Model.write` in order to create or update
        a ``product.product`` record.
        """
        self.ensure_one()
        values = {
            self.KEY_FIELD: self.name,
            'name': self.description,
            'active': True,
        }
        return values

    @api.model
    def _product_changed(self, product, values):
        """Check if existing ``product.product`` record should be changed

        Must return a boolean indicating whether or not an existing
        ``product.product`` record would be changed by this potential
        EDI product record (as represented by the values dictionary
        that would be used to create the EDI product record).

        This is used by the EDI product document preparation process
        to decide whether or not to create an EDI product record.
        """
        return product.name != values['description'] or not product.active

    @api.multi
    def execute(self):
        """Execute product records"""
        super().execute()
        Product = self.env['product.product'].with_context(
            tracking_disable=True,
        )
        doc = self.mapped('doc_id')

        # Update existing products
        for r, batch in batched(self.filtered(lambda x: x.product_id),
                                self.BATCH_SIZE):
            _logger.info(_("%s updating %d-%d"), doc.name, r[0], r[-1])
            for rec in batch:
                rec.product_id.write(rec._product_values())

        # Create new products
        for r, batch in batched(self.filtered(lambda x: not x.product_id),
                                self.BATCH_SIZE):
            _logger.info(_("%s creating %d-%d"), doc.name, r[0], r[-1])
            for rec in batch:
                rec.product_id = Product.create(rec._product_values())
