"""EDI local filesystem connection"""

from datetime import datetime, timedelta
import pathlib
import fnmatch
import base64
import uuid
import logging
import errno
import os
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
    def path_allowed(self, jail_directory, test_path):
        """Is the path within the permitted jail directory?"""
        if jail_directory is None:
            return True

        real_jail_directory = os.path.realpath(jail_directory)
        return os.path.commonpath([real_jail_directory,
                                   os.path.realpath(test_path)]) == real_jail_directory


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

        # Get the jail directory
        gateway = transfer.gateway_id
        jail_directory = gateway.get_jail_path()

        # List local directory
        min_date = (datetime.now() - timedelta(hours=path.age_window))
        for filepath in directory.iterdir():

            # Skip files not matching glob pattern
            if not fnmatch.fnmatch(filepath.name, path.glob):
                continue

            # Did the user try to escape the jail?
            if not self.path_allowed(jail_directory, filepath):
                raise PermissionError(errno.EACCES,
                                      _("Tried to access a folder outside the jail directory %s")
                                      % jail_directory)

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
        Transfer = self.env['edi.transfer']
        outputs = Attachment.browse()
        sent = Attachment.browse()
        directory = conn.joinpath(path.path)

        # Get list of output documents
        min_date = (datetime.now() - timedelta(hours=path.age_window))
        docs = Document.search([
            ('execute_date', '>=', fields.Datetime.to_string(min_date)),
            ('doc_type_id', 'in', path.doc_type_ids.mapped('id'))
        ])

        if not transfer.gateway_id.resend:
            sent = Transfer.search([
                ('create_date', '>', fields.Datetime.to_string(min_date)),
                ('gateway_id', '=', transfer.gateway_id.id),
            ]).mapped('output_ids')

        # Get the jail directory
        gateway = transfer.gateway_id
        jail_directory = gateway.get_jail_path()

        # Send attachments
        for attachment in docs.mapped('output_ids').sorted('id'):
            filepath = directory.joinpath(attachment.datas_fname)

            # Did the user try to escape the jail?
            if not self.path_allowed(jail_directory, filepath):
                raise PermissionError(errno.EACCES,
                                      _("Tried to access a folder outside the jail directory %s")
                                      % jail_directory)

            # Skip files not matching glob pattern
            if not fnmatch.fnmatch(attachment.datas_fname, path.glob):
                continue

            # Skip files of the same size already existing in local directory
            try:
                stat = filepath.stat()
                if stat.st_size == attachment.file_size:
                    continue
            except OSError:
                pass
            else:
                os.unlink(filepath)

            # Skip files already sent, if applicable
            if not transfer.gateway_id.resend and attachment in sent:
                continue

            # Write file with temporary filename
            _logger.info("%s writing %s", transfer.gateway_id.name, filepath)
            temppath = filepath.with_name('.%s~' % uuid.uuid4().hex)
            temppath.write_bytes(base64.b64decode(attachment.datas or b''))

            # Rename temporary file
            temppath.rename(filepath)

            # Record output as sent
            outputs += attachment

        return outputs
