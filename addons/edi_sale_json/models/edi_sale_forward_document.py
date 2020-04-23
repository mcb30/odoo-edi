"""EDI sale order report documents"""

import io
import json
from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include sale order request records to attach the required fields
    for storing the new record types
    """

    _inherit = "edi.document"

    sale_forward_ids = fields.One2many("edi.sale.forward.record", "doc_id", string="Sale Forwards",)
    sale_line_forward_ids = fields.One2many(
        "edi.sale.line.forward.record", "doc_id", string="Sale Line Forwards",
    )

    @api.depends("sale_request_ids", "sale_request_ids.sale_id")
    def _compute_sale_ids(self):
        super()._compute_sale_ids()
        self.mapped("sale_request_ids.sale_id")
        for doc in self:
            doc.sale_ids += doc.mapped("sale_request_ids.sale_id")


class SaleOrder(models.Model):
    """Extend ``sale.order`` to include the EDI sale order report to add the edi document"""

    _inherit = "sale.order"

    edi_sale_forward_id = fields.Many2one(
        "edi.document", string="EDI Sale Order Report", required=False, readonly=True, index=True
    )


class EdiSaleForwardDocument(models.AbstractModel):
    """EDI sale order forwarding document

    This document takes the sale and line forward records and outputs a json file attachment
    """

    _name = "edi.sale.forward.document"
    _inherit = "edi.sale.report.document"
    _description = "Sale Order Forwards"

    _edi_sale_report_via = "edi_sale_forward_id"

    @api.model
    def sale_report_domain(self, _doc):
        """Get sale order search domain

        The default implementation returns all completed sale orders
        for which a report has not yet been generated.
        """
        domain = [("state", "=", "sale")]
        if self._edi_sale_report_via is not None:
            domain.append((self._edi_sale_report_via, "=", False))
        return domain

    @api.model
    def sale_line_report_domain(self, _doc, sales):
        """Get sale order line search domain

        The default implementation returns all completed sale order
        lines associated with the specified sale orders.
        """
        return [("order_id", "in", sales.ids), ("state", "=", "sale")]

    @staticmethod
    def get_customer_ref(partner):
        return str(partner.id)

    def get_customer_values(self, partner):
        return {
            "customer_ref": self.get_customer_ref(partner),
            "customer_type": partner.company_type,
            "name": {"title": partner.title.name, "name": partner.name},
            "address": {
                "first": partner.street,
                "second": partner.street2,
                "town": partner.city,
                "postcode": partner.zip,
                "county": partner.state_id.name,
            },
        }

    def get_sale_values(self, sale, sale_line_recs):
        return {
            "customer_ref": self.get_customer_ref(sale.partner_id),
            "order_ref": sale.sale_ref,
            "lines": [self.get_sale_line_values(line) for line in sale_line_recs],
            # "order_type": "",
            # "priority": "",
        }

    @staticmethod
    def get_sale_line_values(line):

        return {
            "line_ref": line.name,
            "product_ref": line.product_id.default_code,
            "quantity": line.qty_ordered,
        }

    def execute(self, doc):
        """Execute document"""
        super().execute(doc)
        SaleForwards = self.sale_report_record_model(doc)
        SaleLineForwards = self.sale_line_report_record_model(doc)
        sale_recs = SaleForwards.search([("doc_id", "=", doc.id)])
        sale_line_recs = SaleLineForwards.search([("doc_id", "=", doc.id)])

        sale_line_recs_by_sale = dict(sale_line_recs.groupby("sale_id"))

        data = {
            "customers": [],
            "orders": [],
        }

        for sale_rec in sale_recs:

            sale_line_recs = sale_line_recs_by_sale.get(sale_rec.sale_id)
            if not sale_line_recs:
                raise ValueError(_("No records found for sale: %s") % sale_rec.sale_id.name)

            data["customers"].append(self.get_customer_values(sale_rec.partner_id))
            data["orders"].append(self.get_sale_values(sale_rec, sale_line_recs))

        with io.StringIO() as output:
            json.dump(data, output, indent=2)
            data = output.getvalue().encode()

        # Create output attachment
        filename = "sale_forward_%s.json" % datetime.now().strftime("%Y%m%d_%H%M")
        doc.output(filename, data)
