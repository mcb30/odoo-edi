"""EDI sale order report records"""

from odoo import api, fields, models


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include sale order report records"""

    _inherit = "edi.document"

    sale_report_ids = fields.One2many(
        "edi.sale.report.record", "doc_id", string="Sale Order Reports"
    )


class EdiSaleReportRecord(models.Model):
    """EDI sale order report record

    This is the base model for EDI sale order report records.  Each
    row represents a sale order that will be reported upon when the
    document is executed.

    The fields within each record represent the fields within the
    produced document, which may not exactly correspond to fields of
    the ``sale.order`` model.  For example: the document may include a
    column reporting the number of days taken to confirm the order,
    calculated from the picking's creation and confirmation dates.

    Derived models should implement either :meth:`~.record_values` or
    :meth:`~.prepare`.
    """

    _name = "edi.sale.report.record"
    _inherit = "edi.record"
    _description = "Sale Order Report"

    sale_id = fields.Many2one(
        "sale.order", string="Sale Order", required=True, readonly=True, index=True
    )

    _sql_constraints = [
        ("doc_name_uniq", "unique (doc_id, name)", "Each name may appear at most once per document")
    ]

    @api.model
    def record_values(self, sale):
        """Construct EDI record value dictionary

        Accepts a ``sale.order`` record and constructs a
        corresponding value dictionary for an EDI sale order
        report record.
        """
        return {"name": sale.name, "sale_id": sale.id}

    @api.model
    def prepare(self, doc, sales):
        """Prepare records"""
        super().prepare(doc, (self.record_values(sale) for sale in sales))
