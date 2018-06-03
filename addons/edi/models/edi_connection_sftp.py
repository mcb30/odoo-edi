from datetime import datetime, timedelta
import os.path
import fnmatch
import base64
import uuid
import logging
import paramiko
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class SFTPOnlyClient(paramiko.SFTPClient):
    """SFTP-only client

    An SFTP client that keeps the underlying SSH client open until the
    SFTP client is closed.
    """

    @classmethod
    def from_ssh_client(cls, ssh):
        """Construct SFTP client from SSH client"""
        self = cls.from_transport(ssh.get_transport())
        self.__sftp_only_ssh = ssh
        return self

    def close(self):
        """Close SFTP client and the underlying SSH client"""
        super(SFTPOnlyClient, self).close()
        self.__sftp_only_ssh.close()


class EdiConnectionSFTP(models.AbstractModel):
    """EDI SFTP connection

    An EDI SFTP connection is a remote SFTP server used to send and
    receive EDI documents.
    """

    _name = 'edi.connection.sftp'
    _description = "EDI SFTP Connection"

    @api.model
    def connect(self, gateway):
        """Connect to SFTP server"""
        conn = SFTPOnlyClient.from_ssh_client(gateway.ssh_connect())
        if gateway.timeout:
            conn.get_channel().settimeout(gateway.timeout)
        return conn

    @api.model
    def receive_inputs(self, conn, path, transfer):
        """Receive input attachments"""
        Attachment = self.env['ir.attachment']
        inputs = Attachment.browse()

        # List remote directory
        min_date = (datetime.now() - timedelta(hours=path.age_window))
        for dirent in conn.listdir_attr(path.path):

            # Skip files outside the age window
            if datetime.fromtimestamp(dirent.st_mtime) < min_date:
                continue

            # Skip files not matching glob pattern
            if not fnmatch.fnmatch(dirent.filename, path.glob):
                continue

            # Skip files already successfully attached to a document
            if Attachment.search([('res_model', '=', 'edi.document'),
                                  ('res_field', '=', 'input_ids'),
                                  ('res_id', '!=', False),
                                  ('datas_fname', '=', dirent.filename),
                                  ('file_size', '=', dirent.st_size)]):
                continue

            # Receive file
            filepath = os.path.join(path.path, dirent.filename)
            _logger.info("%s receiving %s", transfer.gateway_id.name,
                         filepath)
            data = conn.file(filepath, mode='r').read()

            # Create new attachment for received file
            attachment = Attachment.create({
                'name': dirent.filename,
                'datas_fname': dirent.filename,
                'datas': base64.b64encode(data),
                'res_model': 'edi.document',
                'res_field': 'input_ids',
                })
            inputs += attachment

            # Check received size
            if attachment.file_size != dirent.st_size:
                raise ValidationError(
                    _("File size mismatch (expected %d got %d)") %
                    (dirent.st_size, attachment.file_size)
                    )

        return inputs

    @api.model
    def send_outputs(self, conn, path, transfer):
        """Send output attachments"""
        Document = self.env['edi.document']
        Attachment = self.env['ir.attachment']
        outputs = Attachment.browse()

        # Get names and sizes of existing files
        files = {x.filename: x.st_size for x in conn.listdir_attr(path.path)}

        # Get list of output documents
        min_date = (datetime.now() - timedelta(hours=path.age_window))
        docs = Document.search([
            ('execute_date', '>=', fields.Datetime.to_string(min_date)),
            ('doc_type_id', 'in', path.doc_type_ids.mapped('id'))
            ])

        # Send attachments
        for attachment in docs.mapped('output_ids'):

            # Skip files not matching glob pattern
            if not fnmatch.fnmatch(attachment.datas_fname, path.glob):
                continue

            # Skip files already existing in remote directory
            if (attachment.datas_fname in files and
                attachment.file_size == files[attachment.datas_fname]):
                continue

            # Send file with temporary filename
            temppath = os.path.join(path.path, ('.%s~' % uuid.uuid4().hex))
            filepath = os.path.join(path.path, attachment.datas_fname)
            _logger.info("%s sending %s", transfer.gateway_id.name, filepath)
            data = base64.b64decode(attachment.datas)
            conn.file(temppath, mode='w').write(data)

            # Rename temporary file
            conn.rename(temppath, filepath)

            # Record output as sent
            outputs += attachment

        return outputs
