from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _
from datetime import datetime, timedelta
import os
import os.path
import fnmatch
import base64
import uuid

import logging
_logger = logging.getLogger(__name__)


class DummyConnection(object):
    """Dummy connection object representing connection to local filesystem"""
    def close(self):
        pass


class EdiConnectionLocal(models.AbstractModel):
    """EDI local filesystem connection

    An EDI local filesystem connection is a local filesystem directory
    used to send and receive EDI documents.
    """

    _name = 'edi.connection.local'
    _description = 'EDI Local Connection'

    @api.model
    def connect(self, gateway):
        """Connect to local filesystem"""
        return DummyConnection()

    @api.model
    def receive_inputs(self, conn, path, transfer):
        """Receive input attachments"""
        Attachment = self.env['ir.attachment']
        inputs = Attachment.browse()

        # List local directory
        min_date = (datetime.now() - timedelta(hours=path.age_window))
        for filename in os.listdir(path.path):

            # Skip files not matching glob pattern
            if not fnmatch.fnmatch(filename, path.glob):
                continue

            # Get file information
            filepath = os.path.join(path.path, filename)
            stat = os.stat(filepath)

            # Skip files outside the age window
            if datetime.fromtimestamp(stat.st_mtime) < min_date:
                continue

            # Skip files already successfully attached to a document
            if Attachment.search([('res_model', '=', 'edi.document'),
                                  ('res_field', '=', 'input_ids'),
                                  ('res_id', '!=', False),
                                  ('datas_fname', '=', filename),
                                  ('file_size', '=', stat.st_size)]):
                continue

            # Read file
            _logger.info('%s reading %s', transfer.gateway_id.name, filepath)
            data = open(filepath, mode='rb').read()

            # Create new attachment for received file
            attachment = Attachment.create({
                'name': filename,
                'datas_fname': filename,
                'datas': base64.b64encode(str(data)),
                'res_model': 'edi.document',
                'res_field': 'input_ids',
                })
            inputs += attachment

            # Check received size
            if attachment.file_size != stat.st_size:
                raise ValidationError(
                    _('File size mismatch (expected %d got %d)') %
                    (stat.st_size, attachment.file_size)
                    )

        return inputs

    @api.model
    def send_outputs(self, conn, path, transfer):
        """Send output attachments"""
        Document = self.env['edi.document']

        # Get list of output attachments
        min_date = (datetime.now() - timedelta(hours=path.age_window))
        outputs = Document.search([
            ('execute_date', '>=', fields.Datetime.to_string(min_date)),
            ('doc_type_id', 'in', path.doc_type_ids.mapped('id'))
            ]).mapped('output_ids')

        # Send attachments
        for attachment in outputs:

            # Skip files not matching glob pattern
            if not fnmatch.fnmatch(attachment.datas_fname, path.glob):
                continue

            # Skip files already existing in local directory
            filepath = os.path.join(path.path, attachment.datas_fname)
            try:
                stat = os.stat(filepath)
                if stat.st_size == attachment.file_size:
                    continue
            except OSError:
                pass

            # Write file with temporary filename
            temppath = os.path.join(path.path, ('.%s~' % uuid.uuid4().hex))
            _logger.info('%s writing %s', transfer.gateway_id.name, filepath)
            data = base64.b64decode(attachment.datas)
            open(temppath, mode='wb').write(data)

            # Rename temporary file
            os.rename(temppath, filepath)

        return outputs
