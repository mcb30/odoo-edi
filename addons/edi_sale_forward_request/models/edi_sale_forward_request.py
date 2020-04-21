import os
import json
from jsonschema import validate
from odoo import api, fields, models

# FILEPATH : /srv/udes_closed_11/addons/edi_sale_json_outbound/data/sale_request_schema.json
FILEPATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    *[os.pardir, "data", "sale_request_schema.json"]
)


def partner_address(address):
    """Compute partner address attributes"""
    return {
        "address_line_1": address["first"],
        "address_line_2": address["second"],
        "town": address["town"],
        "county": hasattr(address, "County") and address["county"],
        "postcode": address["postcode"],
    }


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include sale records"""

    _inherit = "edi.document"

    json_partner_ids = fields.One2many(
        "edi.partner.record.info", "doc_id", string="Partners"
    )
    sale_forward_request_ids = fields.One2many(
        "edi.sale.forward.request.record", "doc_id", string="Sale Requests",
    )
    sale_line_forward_request_ids = fields.One2many(
        "edi.sale.line.forward.request.record", "doc_id", string="Sale Line Requests",
    )

    @api.depends("sale_forward_request_ids", "sale_line_forward_request_ids.order_id")
    def _compute_sale_ids(self):
        retvals = super()._compute_sale_ids()
        self.mapped("sale_forward_request_ids.sale_id")
        for doc in self:
            doc.sale_ids += doc.mapped("sale_forward_request_ids.sale_id")
        return retvals


class EdiSaleForwardRequestRecord(models.Model):
    """EDI sale forward request record"""

    _name = "edi.sale.forward.request.record"
    _inherit = "edi.sale.request.record"
    _description = "Sale Request"

    sale_id = fields.Many2one(domain=[("state", "not in", ("done", "cancel"))])


class EdiSaleLineForwardRequestRecord(models.Model):
    """EDI sale line forward request record"""

    _name = "edi.sale.line.forward.request.record"
    _inherit = "edi.sale.line.request.record"
    _description = "Sale Line Request"

    order_id = fields.Many2one(domain=[("state", "not in", ("done", "cancel"))])


class EdiPartnerRecord(models.Model):
    """EDI partner record extended partner record for information pertaining
    to customers."""

    _name = "edi.partner.record.info"
    _inherit = "edi.partner.record"
    _description = "Partner Info"

    email = fields.Char(readonly=True)
    address_line_1 = fields.Char(required=True, readonly=True)
    address_line_2 = fields.Char(readonly=True)
    town = fields.Char(readonly=True)
    county = fields.Char(readonly=True)
    postcode = fields.Char(required=True, readonly=True)
    phone = fields.Char(string="Phone Number", readonly=True)
    mobile = fields.Char(string="Mobile Number", readonly=True)
    is_company = fields.Boolean(default=False, readonly=True)
    country_id = fields.Many2one(
        "res.country", default=lambda self: self.env.ref("base.uk").id
    )

    @api.model
    def target_values(self, record_vals):
        """Construct ``res.partner`` field value dictionary"""
        partner_vals = super().target_values(record_vals)
        partner_vals.update(
            {
                "email": record_vals.get("email"),
                "phone": record_vals.get("phone"),
                "mobile": record_vals.get("mobile"),
                "street": record_vals.get("address_line_1"),
                "street2": record_vals.get("address_line_2"),
                "city": record_vals.get("town"),
                "zip": record_vals.get("postcode"),
                "is_company": record_vals.get("is_company"),
            }
        )
        return partner_vals


class EdiSaleForwardRequestDocument(models.AbstractModel):
    """EDI sale forward request document model"""

    _name = "edi.sale.forward.request.document"
    _inherit = ["edi.partner.document", "edi.sale.request.document"]
    _description = "sale forward request"

    _auto_confirm = True

    @api.model
    def prepare(self, doc):
        """Prepare document"""

        vals = super().prepare(doc)

        EdiSaleRequestRecord = self.sale_request_record_model(doc)
        EdiSaleLineRequestRecord = self.sale_line_request_record_model(doc)
        EdiPartnerRecord = self.partner_record_model(doc)

        schema = None
        with open(FILEPATH) as json_schema:
            schema = json.load(json_schema)

        # Create sales for each input attachment
        for _, data in doc.inputs():

            # Loads byte data and convert to json format
            json_data = json.loads(data)
            validate(json_data, schema)

            for order in json_data["orders"]:
                for line in order["lines"]:
                    EdiSaleLineRequestRecord.create(
                        dict(
                            name="%s/%s" % (order["order_ref"], line["line_ref"]),
                            doc_id=doc.id,
                            order_key=order["order_ref"],
                            product_key=line["product_ref"],
                            qty=line["quantity"],
                        )
                    )

            # Create partner records
            EdiPartnerRecord.prepare(
                doc,
                (
                    {
                        "name": customer["customer_ref"],
                        "full_name": customer["name"]["name"],
                        "title_key": customer["name"].get("title"),
                        "is_company": hasattr(customer, "customer_type")
                        and customer["customer_type"] == "company",
                        **partner_address(customer["address"]),
                    }
                    for customer in json_data["customers"]
                ),
            )

            # Create sale order request records
            EdiSaleRequestRecord.prepare(
                doc,
                (
                    {"name": order["order_ref"], "customer_key": order["customer_ref"]}
                    for order in json_data["orders"]
                ),
            )

        return vals
