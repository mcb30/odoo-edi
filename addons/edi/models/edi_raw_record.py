"""EDI raw import records"""

from odoo import api, fields, models


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include EDI raw import records"""

    _inherit = 'edi.document'

    raw_ids = fields.One2many('edi.raw.record', 'doc_id', string="Raw Records")
    raw_model_id = fields.Many2one(related='raw_ids.model_id',
                                   string="Record Model", readonly=True)
    raw_count = fields.Integer(string="Record Count",
                               compute='_compute_raw_count')
    raw_index_content = fields.Text(related='input_ids.index_content',
                                    readonly=True, prefetch=False)

    @api.multi
    @api.depends('raw_ids', 'raw_ids.doc_id')
    def _compute_raw_count(self):
        """Compute number of raw records (for UI display)"""
        for doc in self:
            doc.raw_count = len(doc.raw_ids)

    @api.multi
    def action_view_raw(self):
        """View raw records"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.raw_model_id.name,
            'res_model': self.raw_model_id.model,
            'views': [(False, 'tree')],
            'domain': [('id', 'in', self.raw_ids.mapped('res_id'))],
        }


class EdiRawRecord(models.Model):
    """EDI raw import record"""

    _name = 'edi.raw.record'
    _inherit = 'edi.record'
    _description = "Raw Record"

    model_id = fields.Many2one('ir.model', string="Model", required=True)
    res_id = fields.Integer(string="Record ID", index=True, required=True)
