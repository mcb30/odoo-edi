"""EDI sale order request documents"""

import logging
from odoo import api, models

_logger = logging.getLogger(__name__)


class EdiSaleRequestDocument(models.AbstractModel):
    """EDI sale order request document

    This is the base model for EDI sale order request documents.  Each
    row represents two collections of EDI records:

    - a collection of EDI sale order request records that, in turn,
      each represent a sale that will be created when the document is
      executed, and

    - a collection of EDI sale order line request records that, in
      turn, each represent a line item within one of the above sale
      orders

    Derived models should implement either :meth:`~.prepare` or
    :meth:`~.sale_request_record_values`.
    """

    _name = 'edi.sale.request.document'
    _inherit = 'edi.document.sync'
    _description = "Sale Requests"

    _auto_confirm = False
    """Automatically confirm sale orders

    Derived models may set this to true in order to automatically
    confirm sale orders as part of document execution.
    """

    BATCH_CONFIRM = 10
    """Batch size for sale order confirmation"""

    @api.model
    def sale_request_record_model(self, doc,
                                  supermodel='edi.sale.request.record'):
        """Get EDI sale request record model class

        Subclasses should never need to override this method.
        """
        return self.record_model(doc, supermodel=supermodel)

    @api.model
    def sale_line_request_record_model(
            self, doc, supermodel='edi.sale.line.request.record'
    ):
        """Get EDI sale line request record model class

        Subclasses should never need to override this method.
        """
        return self.record_model(doc, supermodel=supermodel)

    @api.model
    def sale_request_record_values(self, _data):
        """Construct EDI sale request record value dictionaries

        Must return an iterable of dictionaries, each of which could
        passed to :meth:`~odoo.models.Model.create` in order to create
        an EDI sale request record.
        """
        return self.no_record_values()

    @api.model
    def sale_line_request_record_values(self, _data):
        """Construct EDI sale line request record value dictionaries

        Must return an iterable of dictionaries, each of which could
        passed to :meth:`~odoo.models.Model.create` in order to create
        an EDI sale line request record.
        """
        return self.no_record_values()

    @api.model
    def prepare(self, doc):
        """Prepare document"""
        super().prepare(doc)
        self.sale_request_record_model(doc).prepare(doc, (
            record_vals
            for _fname, data in doc.inputs()
            for record_vals in self.sale_request_record_values(data)
        ))
        self.sale_line_request_record_model(doc).prepare(doc, (
            record_vals
            for _fname, data in doc.inputs()
            for record_vals in self.sale_line_request_record_values(data)
        ))

    @api.model
    def execute(self, doc):
        """Execute document"""
        super().execute(doc)

        # Delete sale orders which no longer have any order lines.
        Partner = self.env['res.partner']
        SaleRequestRecord = self.sale_request_record_model(doc)
        reqs = SaleRequestRecord.search([('doc_id', '=', doc.id)])

        if not doc.fail_fast:
            to_remove = reqs.mapped('sale_id').filtered(lambda s: len(s.mapped('order_line')) == 0)
            orderless_partners = to_remove.mapped('partner_id')
            to_remove.unlink()
            # Remove partners with no orders in the current document and no
            # historic orders.
            domain = [('id', 'in', orderless_partners.mapped('id')),
                      ('sale_order_ids', '=', False)]
            Partner.search(domain).unlink()

        # Automatically confirm sale orders, if applicable
        if self._auto_confirm:
            for r, sales in reqs.mapped('sale_id').batched(self.BATCH_CONFIRM):
                _logger.info("%s confirming %d-%d", doc.name, r[0], r[-1])
                with self.statistics() as stats:
                    sales.action_confirm()
                    self.recompute()
                _logger.info("%s confirmed %d-%d in %.2fs, %d queries",
                             doc.name, r[0], r[-1], stats.elapsed, stats.count)
