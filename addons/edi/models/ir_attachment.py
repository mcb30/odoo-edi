from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

import fnmatch


class IrAttachment(models.Model):

    _inherit = "ir.attachment"

    @api.model
    def check(self, mode, values=None):
        """
        Extend to bypass check for EDI Document attachments when the user is accessing
        input/outputs, so long as the user has access to EDI Documents
        """
        if not self.env.is_superuser():
            edi_doc_model = "edi.document"
            edi_doc_fields = ["input_ids", "output_ids"]

            default_res_model = self.env.context.get("default_res_model")
            default_res_field = self.env.context.get("default_res_field")

            res_models = list(dict.fromkeys(self.sudo().mapped("res_model")))
            res_fields = list(dict.fromkeys(self.sudo().mapped("res_field")))

            if (
                self.env.user.has_group("edi.group_edi_document_type_view")
                and (
                    (res_models and len(res_models) == 1 and res_models[0] == edi_doc_model)
                    or default_res_model == edi_doc_model
                )
                and (
                    (
                        len(res_fields) <= len(edi_doc_fields)
                        and all([field in edi_doc_fields for field in res_fields])
                    )
                    or default_res_field in edi_doc_fields
                )
            ):
                return True

        return super().check(mode=mode, values=values)

    @api.constrains("res_model")
    def check_filename(self):
        """Validates attachment filename against the format defined in 'glob'"""
        EdiDocument = self.env["edi.document"]
        EdiGatewayPath = self.env["edi.gateway.path"]
        edi_document_attachments = self.filtered(lambda a: a.res_model == "edi.document")
        for attachment in edi_document_attachments:
            doc = EdiDocument.browse(attachment.res_id)
            if doc.doc_type_id.enforce_filename:
                recs = EdiGatewayPath.search([("doc_type_ids", "=", doc.doc_type_id.id)])
                if recs:
                    globs = recs.mapped("glob")
                    for input_file in doc.input_ids:
                        passed = bool(
                            any(fnmatch.fnmatch(input_file.display_name, glob) for glob in globs)
                        )
                        if not passed:
                            raise ValidationError(_("Invalid filename when trying to attach."))
