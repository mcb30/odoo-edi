"""EDI product documents"""

from base64 import b64decode
import logging
from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools.translate import _
from odoo.addons.edi.tools import batched, Comparator

_logger = logging.getLogger(__name__)


class EdiProductDocument(models.AbstractModel):
    """EDI product document

    This is the base model for EDI product documents.  Each row
    represents a collection of EDI product records that, in turn,
    represent a product that will be created or updated when the
    document is executed.

    All input attachments are parsed to generate a list of potential
    EDI product records, represented in the form of a values
    dictionary that could be used to create the EDI product record.

    Product definitions typically change infrequently.  To minimise
    unnecessary duplication, any EDI product records that would not
    result in a new or modified ``product.product`` record will be
    automatically elided from the document.

    Derived models should implement :meth:`~._record_values`.
    """

    BATCH_SIZE = 1000
    """Batch size for processing EDI product records

    This is used to obtain a sensible balance between the number of
    database queries to the ``product.product`` table and the number
    of records returned in each query.
    """

    _name = 'edi.product.document'
    _inherit = 'edi.document.model'
    _description = "Products"

    @api.model
    def _record_model(self, doc):
        """Get corresponding EDI product record model"""
        rec_type_id = doc.doc_type_id.rec_type_ids.ensure_one()
        return self.env[rec_type_id.model_id.model]

    @api.model
    def _record_values(self, _data):
        """Construct EDI product record value dictionaries

        Must return an iterable of dictionaries, each of which could
        passed to :meth:`~odoo.models.Model.create` or
        :meth:`~odoo.models.Model.write` in order to create or update
        an EDI product record.
        """
        return ()

    @api.model
    def _prepare_batch(self, doc, batch, comparator):
        """Prepare batch of records"""
        Product = self.env['product.product'].with_context(active_test=False)
        Template = self.env['product.template'].with_context(active_test=False)
        EdiRecord = self._record_model(doc)

        # Look up existing products
        key = EdiRecord.KEY_FIELD
        products = Product.search([(key, 'in', [x['name'] for x in batch])])
        products_by_key = {getattr(x, key): x for x in products}

        # Cache product templates to minimise database lookups
        templates = Template.browse(products.mapped('product_tmpl_id.id'))
        templates.mapped('name')

        # Create EDI records
        for record_vals in batch:

            # Skip unchanged products
            product = products_by_key.get(record_vals['name'])
            if product:
                product_vals = EdiRecord._product_values(record_vals)
                if all(comparator[k](getattr(product, k), v)
                       for k, v in product_vals.items()):
                    continue

            # Create EDI product record
            record_vals['doc_id'] = doc.id
            if product:
                record_vals['product_id'] = product.id
            EdiRecord.create(record_vals)

    @api.model
    def prepare(self, doc):
        """Prepare document"""

        # Sanity check
        if not doc.input_ids:
            raise UserError(_("Missing input attachment"))

        # Construct product comparator
        comparator = Comparator(self.env['product.product'])

        # Process documents in batches of product records for efficiency
        record_vals = (
            record_vals
            for attachment in doc.input_ids.sorted('id')
            for record_vals in self._record_values(b64decode(attachment.datas))
        )
        for r, batch in batched(record_vals, self.BATCH_SIZE):
            _logger.info(_("%s preparing %d-%d"), doc.name, r[0], r[-1])
            self._prepare_batch(doc, batch, comparator)
