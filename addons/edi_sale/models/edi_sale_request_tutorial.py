"""EDI sale request tutorial

This example shows the code required to implement a simple EDI sale
request document format comprising a CSV file with a fixed list of
columns:

* Order reference
* Customer name
* Product reference
* Quantity
"""

import csv
import re
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _
from odoo.tools.misc import OrderedSet


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include sale tutorial records"""

    _inherit = 'edi.document'

    customer_tutorial_ids = fields.One2many(
        'edi.sale.customer.tutorial.record', 'doc_id',
        string="Sale Requests",
    )
    sale_request_tutorial_ids = fields.One2many(
        'edi.sale.request.tutorial.record', 'doc_id',
        string="Sale Requests",
    )
    sale_line_request_tutorial_ids = fields.One2many(
        'edi.sale.line.request.tutorial.record', 'doc_id',
        string="Sale Line Requests",
    )

    @api.multi
    @api.depends('sale_request_tutorial_ids',
                 'sale_line_request_tutorial_ids.order_id')
    def _compute_order_ids(self):
        super()._compute_order_ids()
        for doc in self:
            # TODO: fix the varied use of names 'sale' and 'order' to be consistent.
            doc.order_ids += doc.mapped('sale_request_tutorial_ids.sale_id')


class EdiSaleCustomerTutorialRecord(models.Model):
    """EDI customer tutorial record

    This subclass may be omitted if no extra functionality is required
    beyond that provided by the base ``edi.partner.record``.
    """

    _name = 'edi.sale.customer.tutorial.record'
    _inherit = 'edi.partner.record'
    _description = "Customer"

    @api.model
    def target_values(self, record_vals):
        partner_vals = super().target_values(record_vals)
        partner_vals.update({
            'customer': True
        })
        return partner_vals


class EdiSaleRequestTutorialRecord(models.Model):
    """EDI sale request tutorial record

    This subclass may be omitted if no extra functionality is required
    beyond that provided by the base ``edi.sale.request.record``.
    """

    _name = 'edi.sale.request.tutorial.record'
    _inherit = 'edi.sale.request.record'
    _description = "Sale Request"

    _edi_sync_domain = [('state', 'not in', ('done', 'cancel'))]


class EdiSaleLineRequestTutorialRecord(models.Model):
    """EDI sale line request tutorial record

    This subclass may be omitted if no extra functionality is required
    beyond that required by the base ``edi.sale.line.request.record``.
    """

    _name = 'edi.sale.line.request.tutorial.record'
    _inherit = 'edi.sale.line.request.record'
    _description = "Sale Line Request"

    order_key = fields.Char(edi_relates_domain=[('state', 'not in',
                                                 ('done', 'cancel'))])


class EdiSaleRequestTutorialDocument(models.AbstractModel):
    """EDI sale request tutorial document model"""

    _name = 'edi.sale.request.tutorial.document'
    _inherit = 'edi.sale.request.document'
    _description = "Tutorial sale request CSV file"""

    @api.model
    def prepare(self, doc):
        """Prepare document"""
        super().prepare(doc)
        EdiSaleRequestRecord = self.sale_request_record_model(doc)
        EdiSaleLineRequestRecord = self.sale_line_request_record_model(doc)
        EdiSaleCustomerTutorialRecord = self.env['edi.sale.customer.tutorial.record']

        pricelist = self.env.ref('product.list0')

        # Create sales for each input attachment
        for fname, data in doc.inputs():
            # Create sale request records and construct list of orders
            customer_orders = OrderedSet()
            orders = OrderedSet()

            reader = csv.reader(data.decode().splitlines())
            for order, customer, product, qty in reader:
                orders.add(order)
                customer_orders.add((order, customer))
                EdiSaleLineRequestRecord.create({
                    'name': '%s/%s' % (order, product),
                    'doc_id': doc.id,
                    'order_key': order,
                    'product_key': product,
                    'qty': float(qty),
                })

            print(customer_orders)
            for order, customer in customer_orders:
                # TODO: build list of dicts then pass to the two prepares.
                print(order, customer)
                EdiSaleCustomerTutorialRecord.prepare(doc, ({
                    'name': customer,
                    'title_key': 'Miss',  # TODO: Move title to file. Currently cannot create partner with no title.
                    'full_name': customer,
                },))
                EdiSaleRequestRecord.prepare(doc, ({
                    'name': order,
                    'customer_key': customer,
                    'pricelist_id': pricelist.id,
                },))