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

        SaleRequestRecord = self.sale_request_record_model(doc)
        reqs = SaleRequestRecord.search([('doc_id', '=', doc.id)])

        if not doc.fail_fast:
            self.remove_sales_for_invalid_partner_updates(doc)
            self.remove_empty_orders(doc, reqs)
            self.report_invalid_records(doc)
            self._clear_errors(doc)

        # Automatically confirm sale orders, if applicable
        if self._auto_confirm:
            for r, sales in reqs.mapped('sale_id').batched(self.BATCH_CONFIRM):
                _logger.info("%s confirming %d-%d", doc.name, r[0], r[-1])
                with self.statistics() as stats:
                    sales.action_confirm()
                    self.recompute()
                _logger.info("%s confirmed %d-%d in %.2fs, %d queries",
                             doc.name, r[0], r[-1], stats.elapsed, stats.count)

    def remove_sales_for_invalid_partner_updates(self, doc):
        """Remove sale orders for partners with invalid updates."""
        PartnerRecord = self.partner_record_model(doc)
        SaleRequestRecord = self.sale_request_record_model(doc)

        # Identify EDI partners with invalid updates which are either parents
        # or individuals.
        bad_partners = PartnerRecord.search([('error', '!=', False),
                                             ('parent_id', '=', False),
                                             ('doc_id', '=', doc.id)])
        # Identify EDI partners which are children of invalid parents.
        bad_children = PartnerRecord.search([('parent_id', 'in', bad_partners.mapped('partner_id').ids)])
        bad_partners |= bad_children
        # Identify sale orders created for invalid partners.
        bad_sales = SaleRequestRecord.search([('doc_id', '=', doc.id),
                                              ('customer_id', 'in', bad_partners.mapped('partner_id').ids)])
        bad_sales.mapped('sale_id').unlink()
        return

    def remove_empty_orders(self, doc, reqs):
        """Delete sale orders with no order lines, and related partners."""
        Partner = self.env['res.partner']

        to_remove = reqs.mapped('sale_id').filtered(lambda s: len(s.mapped('order_line')) == 0)
        orderless_partners = to_remove.mapped('partner_id')
        to_remove.unlink()
        # Remove partners with no orders in the current document and no
        # historic orders.
        domain = [('id', 'in', orderless_partners.mapped('id')),
                  ('sale_order_ids', '=', False)]
        Partner.search(domain).unlink()
        return

    def report_invalid_records(self, doc):
        """Post a message listing records that were not processed."""
        PartnerRecord = self.partner_record_model(doc)
        SaleLineRequestRecord = self.sale_line_request_record_model(doc)
        SaleRequestRecord = self.sale_request_record_model(doc)

        error_domain = [('doc_id', '=', doc.id), ('error', '!=', False)]
        lines = SaleLineRequestRecord.search(error_domain)
        orders = SaleRequestRecord.search(error_domain)
        partners = PartnerRecord.search(error_domain)
        message = []
        if lines:
            message.extend(self._build_invalid_order_lines_report(lines))
        if orders:
            message.extend(self._build_invalid_orders_report(orders))
        if partners:
            message.extend(self._build_invalid_partners_report(partners))
        if message:
            doc.sudo().with_context(tracking_disable=False).message_post(body='\n'.join(message),
                                                                         content_subtype='plaintext')
        return

    def _build_invalid_order_lines_report(self, lines):
        report_lines = ['Missing order lines']
        for line in lines:
            item = '\t'.join([str(x) for x in self._extract_invalid_order_line(line)])
            report_lines.append(item)
        return report_lines

    def _extract_invalid_order_line(self, line):
        return [line.order_key, line.product_key, int(line.qty), line.error]

    def _build_invalid_orders_report(self, orders):
        report_lines = ['Missing orders']
        for order in orders:
            item = '\t'.join([str(x) for x in self._extract_invalid_order_order(order)])
            report_lines.append(item)
        return report_lines

    def _extract_invalid_order(self, order):
        return [order.name, order.error]

    def _build_invalid_partners_report(self, partners):
        report_lines = ['Missing partners']
        for partner in partners:
            item = '\t'.join([str(x) for x in self._extract_invalid_partner(partner)])
            report_lines.append(item)
        return report_lines

    def _extract_invalid_partner(self, partner):
        return [partner.error.replace('\n', ' ')]

    def _clear_errors(self, doc):
        PartnerRecord = self.partner_record_model(doc)
        SaleLineRequestRecord = self.sale_line_request_record_model(doc)
        SaleRequestRecord = self.sale_request_record_model(doc)

        error_domain = [('doc_id', '=', doc.id), ('error', '!=', False)]
        for model in (PartnerRecord, SaleLineRequestRecord, SaleRequestRecord):
            records = model.search(error_domain)
            records.write({'error': False})
