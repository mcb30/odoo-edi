"""EDI document autocreation wizard"""

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class EdiAutocreateWizard(models.TransientModel):
    """EDI document autocreation wizard"""

    _name = "edi.document.autocreate"
    _description = "EDI document autocreation wizard"

    input_ids = fields.Many2many("ir.attachment", string="Inputs")
    doc_type_ids = fields.Many2many(
        "edi.document.type",
        string="Restricted Document Types",
        help="Leave blank to allow all document types",
    )
    doc_ids = fields.Many2many("edi.document", string="Documents")

    def autocreate(self):
        """Autocreate EDI documents"""
        self.ensure_one()
        inputs = self.input_ids.sorted("id")
        if not inputs:
            raise UserError(_("You must add at least one input attachment"))
        docs = self.doc_type_ids.autocreate(inputs)
        self.doc_ids = docs
        return docs

    @api.model
    def action_display(self):
        """Display autocreated EDI documents"""
        self.ensure_one()
        action = self.env.ref("edi.document_action").sudo().read()[0]
        action["target"] = "main"
        action["name"] = _("Autocreated EDI Documents")
        action["domain"] = [("id", "in", self.doc_ids.ids)]
        action["context"] = {"create": False}
        return action

    def action_create(self):
        """Autocreate EDI documents"""
        self.autocreate()
        return self.action_display()

    def action_prepare(self):
        """Autocreate and prepare EDI documents"""
        self.autocreate()
        for doc in self.doc_ids:
            doc.action_prepare()
        return self.action_display()

    def action_execute(self):
        """Autocreate and execute EDI documents"""
        self.autocreate()
        for doc in self.doc_ids:
            doc.action_execute()
        return self.action_display()
