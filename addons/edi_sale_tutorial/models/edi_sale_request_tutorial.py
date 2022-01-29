"""EDI sale request tutorial

This example shows the code required to implement a simple EDI sale
request document format comprising a CSV file with a fixed list of
columns:

* Customer name
* Order reference
* Product reference
* Quantity
"""

import csv
from odoo import api, fields, models
from odoo.tools.misc import OrderedSet


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include sale tutorial records"""

    _inherit = "edi.document"

    sale_request_tutorial_ids = fields.One2many(
        "edi.sale.request.tutorial.record",
        "doc_id",
        string="Sale Requests",
    )
    sale_line_request_tutorial_ids = fields.One2many(
        "edi.sale.line.request.tutorial.record",
        "doc_id",
        string="Sale Line Requests",
    )

    @api.depends("sale_request_tutorial_ids", "sale_line_request_tutorial_ids.order_id")
    def _compute_sale_ids(self):
        super()._compute_sale_ids()
        self.mapped("sale_request_tutorial_ids.sale_id")
        for doc in self:
            doc.sale_ids += doc.mapped("sale_request_tutorial_ids.sale_id")


class EdiSaleRequestTutorialRecord(models.Model):
    """EDI sale request tutorial record

    This subclass may be omitted if no extra functionality is required
    beyond that provided by the base ``edi.sale.request.record``.
    """

    _name = "edi.sale.request.tutorial.record"
    _inherit = "edi.sale.request.record"
    _description = "Sale Request"

    sale_id = fields.Many2one(domain=[("state", "not in", ("done", "cancel"))])


class EdiSaleLineRequestTutorialRecord(models.Model):
    """EDI sale line request tutorial record

    This subclass may be omitted if no extra functionality is required
    beyond that required by the base ``edi.sale.line.request.record``.
    """

    _name = "edi.sale.line.request.tutorial.record"
    _inherit = "edi.sale.line.request.record"
    _description = "Sale Line Request"

    order_id = fields.Many2one(domain=[("state", "not in", ("done", "cancel"))])


class EdiSaleRequestTutorialDocument(models.AbstractModel):
    """EDI sale request tutorial document model"""

    _name = "edi.sale.request.tutorial.document"
    _inherit = ["edi.partner.document", "edi.sale.request.document"]
    _description = "Tutorial sale request CSV file" ""

    _auto_confirm = True

    @api.model
    def prepare(self, doc):
        """Prepare document"""
        super().prepare(doc)
        EdiSaleRequestRecord = self.sale_request_record_model(doc)
        EdiSaleLineRequestRecord = self.sale_line_request_record_model(doc)
        EdiPartnerRecord = self.partner_record_model(doc)

        # Create sales for each input attachment
        for _fname, data in doc.inputs():

            # Create sale line request records and construct list of orders
            customers = OrderedSet()
            orders = OrderedSet()
            reader = csv.reader(data.decode().splitlines())
            for customer, order, product, qty in reader:
                customers.add(customer)
                orders.add((order, customer))
                EdiSaleLineRequestRecord.create(
                    {
                        "name": "%s/%s" % (order, product),
                        "doc_id": doc.id,
                        "order_key": order,
                        "product_key": product,
                        "qty": float(qty),
                    }
                )

            # Create partner records
            EdiPartnerRecord.prepare(
                doc,
                (
                    {
                        "name": customer,
                        "full_name": customer,
                    }
                    for customer in customers
                ),
            )

            # Create sale order request records
            EdiSaleRequestRecord.prepare(
                doc,
                (
                    {
                        "name": order,
                        "customer_key": customer,
                    }
                    for order, customer in orders
                ),
            )
