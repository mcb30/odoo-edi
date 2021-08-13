from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

import fnmatch

class IrAttachment(models.Model):

    _inherit = 'ir.attachment'

    @api.constrains('res_model')
    def check_filename(self):
        EdiDocument = self.env["edi.document"]
        EdiGatewayPath = self.env["edi.gateway.path"]
        self.ensure_one()
        if self.res_model == 'edi.document':
            doc = EdiDocument.browse(self.res_id)
            if doc.doc_type_id.enforce_filename:
                recs = EdiGatewayPath.search([('doc_type_ids', '=', doc.doc_type_id.id)])
                globs = recs.mapped('glob')
                for input in doc.input_ids:
                    passed = False
                    for glob in globs:
                        if fnmatch.fnmatch(input.datas_fname, glob):
                            passed = True
                            break
                    if not passed:
                        raise ValidationError(_('Invalid filename when trying to attach.'))