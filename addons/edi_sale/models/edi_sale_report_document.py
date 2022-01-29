"""EDI sale order report documents"""

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class SaleOrder(models.Model):
    """Extend ``sale.order`` to include the EDI sale order report"""

    _inherit = "sale.order"

    edi_sale_report_id = fields.Many2one(
        "edi.document", string="EDI Sale Order Report", required=False, readonly=True, index=True
    )


class EdiSaleReportDocument(models.AbstractModel):
    """EDI sale order report document

    This is the base model for EDI sale order report documents.  Each
    row represents two collections of EDI records:

    - a collection of EDI sale order report records that, in turn,
      each represent a sale order that will be reported upon when the
      document is executed, and

    - a collection of EDI sale order line report records that, in
      turn, each represent a collection of line items within the above
      sale orders

    Derived models should implement :meth:`~.sale_line_report_list`
    and :meth:`~.execute`, and may choose to implement
    :meth:`~.sale_report_domain` and :meth:`~.sale_line_report_domain`.
    """

    _name = "edi.sale.report.document"
    _inherit = "edi.document.model"
    _description = "Sale Order Reports"

    _edi_sale_report_via = "edi_sale_report_id"
    """Report record field

    This field is used to record the EDI document used to report upon
    a ``sale.order``.  It may be overridden if there is a need to
    report more than once upon a single ``sale.order`` record.
    """

    @api.model
    def sale_report_record_model(self, doc, supermodel="edi.sale.report.record"):
        """Get EDI sale order report record model class

        Subclasses should never need to override this method.
        """
        return self.record_model(doc, supermodel=supermodel)

    @api.model
    def sale_line_report_record_model(self, doc, supermodel="edi.sale.line.report.record"):
        """Get EDI sale order line report record model class

        Subclasses should never need to override this method.
        """
        return self.record_model(doc, supermodel=supermodel)

    @api.model
    def sale_report_domain(self, _doc):
        """Get sale order search domain

        The default implementation returns all completed sale orders
        for which a report has not yet been generated.
        """
        domain = [("state", "=", "done")]
        if self._edi_sale_report_via is not None:
            domain.append((self._edi_sale_report_via, "=", False))
        return domain

    @api.model
    def sale_line_report_domain(self, _doc, sales):
        """Get sale order line search domain

        The default implementation returns all completed sale order
        lines associated with the specified sale orders.
        """
        return [("order_id", "in", sales.ids), ("state", "=", "done")]

    @api.model
    def sale_line_report_list(self, _doc, lines):
        """Get list of sale order lines for which reports should be generated

        Returns an iterable of ``sale.order.line`` recordsets.  Each
        recordset in the iterable will result in the creation of a
        single EDI sale order line report record.

        Note that a recordset is itself an iterable of (singleton)
        recordsets.  This method may therefore return a single
        ``sale.order.line`` recordset, in which case each individual
        ``sale.order.line`` record will result in the creation of a
        separate EDI sale order line report record.  The default
        implementation does exactly this.
        """
        return lines

    @api.model
    def prepare(self, doc):
        """Prepare document"""
        # pylint: disable=redefined-outer-name
        SaleReport = self.sale_report_record_model(doc)
        SaleLineReport = self.sale_line_report_record_model(doc)
        SaleOrder = self.env["sale.order"]
        SaleOrderLine = self.env["sale.order.line"]
        # Lock sale orders to prevent concurrent report generation attempts
        sales = SaleOrder.search(self.sale_report_domain(doc), order="id")
        if self._edi_sale_report_via is not None:
            sales.write({self._edi_sale_report_via: False})
        # Construct sale order line list, if applicable
        if SaleLineReport is not None:
            lines = SaleOrderLine.search(
                self.sale_line_report_domain(doc, sales), order="order_id, id"
            )
            linelist = (
                x.with_prefetch(lines._prefetch_ids) for x in self.sale_line_report_list(doc, lines)
            )
        # Prepare records
        SaleReport.prepare(doc, sales)
        if SaleLineReport is not None:
            SaleLineReport.prepare(doc, linelist)

    @api.model
    def execute(self, doc):
        """Execute document"""
        super().execute(doc)
        # Mark sale orders as reported upon by this document
        doc.ensure_one()
        SaleReport = self.sale_report_record_model(doc)
        sale_reports = SaleReport.search([("doc_id", "=", doc.id)])
        sales = sale_reports.mapped("sale_id")
        if self._edi_sale_report_via is not None:
            reported_sales = sales.filtered(self._edi_sale_report_via)
            if reported_sales:
                raise UserError(
                    _("Report already generated for %s") % ", ".join(reported_sales.mapped("name"))
                )
            sales.write({self._edi_sale_report_via: doc.id})
