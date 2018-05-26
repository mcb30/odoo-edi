import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class Message(models.Model):

    _inherit = 'mail.message'

    edi_attachment_audit_ids = fields.One2many('edi.attachment.audit',
                                               'mail_message_id')

    @api.multi
    def message_format(self):
        """Add attachment audit information to mail messages"""
        values = super(Message, self).message_format()
        for value in values:
            msg = self.browse(value['id'])
            if msg.edi_attachment_audit_ids:
                edi_attachment_audit_ids = msg.edi_attachment_audit_ids.read([
                    'datas_fname', 'file_size', 'checksum',
                    ])
                value['edi_attachment_audit_ids'] = edi_attachment_audit_ids
        return values


class EdiAttachmentAudit(models.Model):

    _name = 'edi.attachment.audit'
    _description = 'EDI Attachment Audit'

    # Associated record
    mail_message_id = fields.Many2one('mail.message', string='Message',
                                      required=True, index=True,
                                      readonly=True, ondelete='cascade')

    # Audit information
    attachment_id = fields.Many2one('ir.attachment', string='Attachment',
                                    index=True, readonly=True,
                                    ondelete='set null')
    datas_fname = fields.Char(string='File Name', readonly=True)
    file_size = fields.Integer(string='File Size', readonly=True)
    checksum = fields.Char(string='Checksum', readonly=True)

    @api.model
    def audit_attachments(self, thread, attachments, **kwargs):
        """Create audit log of attachments"""
        if attachments:
            audit_values = [(0, 0, {'attachment_id': x.id,
                                    'datas_fname': x.datas_fname,
                                    'file_size': x.file_size,
                                    'checksum': x.checksum})
                            for x in attachments]
            thread.message_post(attachment_ids=[x.id for x in attachments],
                                edi_attachment_audit_ids=audit_values,
                                **kwargs)
