"""EDI local filesystem connection"""

from datetime import datetime, timedelta
import pathlib
import fnmatch
import base64
import uuid
import logging
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class EdiConnectionLocal(models.AbstractModel):
    """EDI local filesystem connection

    An EDI local filesystem connection is a local filesystem directory
    used to send and receive EDI documents.
    """

    _name = 'edi.connection.local'
    _inherit = 'edi.connection.model'
    _description = "EDI Local Connection"

    @api.model
    def connect(self, _gateway):
        """Connect to local filesystem"""
        # Interestingly, this appears to be the only viably portable
        # way to construct a Path object for the filesystem root.
        return pathlib.Path(pathlib.Path().absolute().root)

    @api.model
    def receive_inputs(self, conn, path, transfer):
        """Receive input attachments"""
        Attachment = self.env['ir.attachment']
        inputs = Attachment.browse()
        directory = conn.joinpath(path.path)

        # List local directory
        min_date = (datetime.now() - timedelta(hours=path.age_window))
        for filepath in directory.iterdir():

            # Skip files not matching glob pattern
            if not fnmatch.fnmatch(filepath.name, path.glob):
                continue

            # Get file information
            stat = filepath.stat()

            # Skip files outside the age window
            if datetime.fromtimestamp(stat.st_mtime) < min_date:
                continue

            # Skip files already successfully attached to a document
            if Attachment.search([('res_model', '=', 'edi.document'),
                                  ('res_field', '=', 'input_ids'),
                                  ('res_id', '!=', False),
                                  ('datas_fname', '=', filepath.name),
                                  ('file_size', '=', stat.st_size)]):
                continue

            # Read file
            _logger.info("%s reading %s", transfer.gateway_id.name, filepath)
            data = filepath.read_bytes()

            # Create new attachment for received file
            attachment = Attachment.create({
                'name': filepath.name,
                'datas_fname': filepath.name,
                'datas': base64.b64encode(data),
                'res_model': 'edi.document',
                'res_field': 'input_ids',
            })
            inputs += attachment

            # Check received size
            if attachment.file_size != stat.st_size:
                raise ValidationError(
                    _("File size mismatch (expected %d got %d)") %
                    (stat.st_size, attachment.file_size)
                )

        return inputs

    @api.model
    def send_outputs(self, conn, path, transfer):
        """Send output attachments"""
        Document = self.env['edi.document']
        Attachment = self.env['ir.attachment']
        outputs = Attachment.browse()
        directory = conn.joinpath(path.path)

        # Get list of output documents
        min_date = (datetime.now() - timedelta(hours=path.age_window))
        docs = Document.search([
            ('execute_date', '>=', fields.Datetime.to_string(min_date)),
            ('doc_type_id', 'in', path.doc_type_ids.mapped('id'))
        ])

        # Send attachments
        for attachment in docs.mapped('output_ids').sorted('id'):

            # Skip files not matching glob pattern
            if not fnmatch.fnmatch(attachment.datas_fname, path.glob):
                continue

            # Skip files already existing in local directory
            filepath = directory.joinpath(attachment.datas_fname)
            try:
                stat = filepath.stat()
                if stat.st_size == attachment.file_size:
                    continue
            except OSError:
                pass

            # Write file with temporary filename
            _logger.info("%s writing %s", transfer.gateway_id.name, filepath)
            temppath = filepath.with_name('.%s~' % uuid.uuid4().hex)
            temppath.write_bytes(base64.b64decode(attachment.datas))

            # Rename temporary file
            temppath.rename(filepath)

            # Record output as sent
            outputs += attachment

        return outputs
