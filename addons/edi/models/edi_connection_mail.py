"""EDI Mail connection"""

from contextlib import contextmanager
from datetime import datetime, timedelta
import fnmatch
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class EdiConnectionMail(models.AbstractModel):
    """EDI Mail connection

    An EDI Mail connection is used to send EDI documents by e-mail.
    """

    _name = 'edi.connection.mail'
    _inherit = 'edi.connection.model'
    _description = "EDI Mail Connection"

    @contextmanager
    @api.model
    def connect(self, _gateway):
        """Connect to mail server"""
        yield

    @api.model
    def receive_inputs(self, conn, path, transfer):
        """Receive input attachments"""
        pass

    @api.model
    def send_outputs(self, _conn, path, _transfer):
        """Send output attachments"""
        Attachment = self.env['ir.attachment']
        Document = self.env['edi.document']
        Mail = self.env['mail.mail']

        # Get message template
        template = self.env.ref('edi.mail_template')

        # Get list of output documents
        min_date = (datetime.now() - timedelta(hours=path.age_window))
        docs = Document.search([
            ('execute_date', '>=', fields.Datetime.to_string(min_date)),
            ('doc_type_id', 'in', path.doc_type_ids.mapped('id')),
            ('output_ids', '!=', False),
        ])

        # Identify attachments already sent via this path
        sent = Mail.search([
            ('date', '>=', fields.Datetime.to_string(min_date)),
            ('model', '=', 'edi.gateway.path'),
            ('res_id', '=', path.id),
            ('state', '=', 'sent'),
        ]).mapped('attachment_ids')

        # Send documents
        outputs = Attachment.browse()
        for doc in docs:

            # Identify applicable attachments
            attachments = doc.output_ids.sorted('id').filtered(
                lambda x: fnmatch.fnmatch(x.name, path.glob)
            )

            # Skip documents where all attachments have already been sent
            if attachments <= sent:
                continue
            outputs += attachments

            # Create e-mail
            vals = template.generate_email(doc.id)
            vals['model'] = 'edi.gateway.path'
            vals['res_id'] = path.id
            vals['email_to'] = path.path
            vals['attachment_ids'] = [(6, 0, [x.id for x in attachments])]
            mail = Mail.create(vals)

            # Send e-mail
            mail.send(raise_exception=True)

        return outputs
