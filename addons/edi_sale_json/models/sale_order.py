from odoo import api, fields, models, _


class EdiDocumentType(models.Model):
    _inherit = "edi.document.type"

    sale_report = fields.Boolean(default=False, index=True)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_edi_docs(self):
        doc_types = self.env["edi.document.type"].search([("sale_report", "=", True)])
        return doc_types

    edi_doc_type_ids = fields.Many2many(
        "edi.document.type", default=lambda self: self._get_edi_docs()
    )

    def action_edi_autocreate(self):
        """Create EDI pick report"""
        self.edi_doc_type_ids.autoemit()
        return True

    def action_confirm(self):
        res = super().action_confirm()
        if res:
            res &= self.action_edi_autocreate()
        return res
