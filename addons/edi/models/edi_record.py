from odoo import api, fields, models

import logging
_logger = logging.getLogger(__name__)


class EdiRecordType(models.Model):

    _name = 'edi.record.type'
    _description = 'EDI Record Type'
    _order = 'sequence, id'

    name = fields.Char(string='Name', required=True, index=True)
    model_id = fields.Many2one('ir.model', string='Record Model',
                               required=True)
    doc_type_ids = fields.Many2many('edi.document.type',
                                    string='Document Types')
    sequence = fields.Integer(string='Sequence', help='Application Order')


class EdiRecord(models.AbstractModel):

    _name = 'edi.record'
    _description = 'EDI Record'
    _order = 'doc_id, id'

    name = fields.Char(string='Name', required=True, readonly=True,
                       index=True)
    doc_id = fields.Many2one('edi.document', string='EDI Document',
                             required=True, readonly=True, index=True,
                             ondelete='cascade')

    @api.multi
    def execute(self):
        """Execute records"""
        # Nothing to do
