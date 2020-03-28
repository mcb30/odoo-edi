"""EDI SFTP connection"""

from contextlib import closing
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
from ..tools import batched

_logger = logging.getLogger(__name__)


class SFTPOnlyClient(paramiko.SFTPClient):
    """SFTP-only client

    An SFTP client that keeps the underlying SSH client open until the
    SFTP client is closed.
    """

    @classmethod
    def from_ssh_client(cls, ssh):
        """Construct SFTP client from SSH client"""
        # pylint: disable=attribute-defined-outside-init
        self = cls.from_transport(ssh.get_transport())
        self.__sftp_only_ssh = ssh
        return self

    def close(self):
        """Close SFTP client and the underlying SSH client"""
        super().close()
        self.__sftp_only_ssh.close()


class EdiConnectionSFTP(models.AbstractModel):
    """EDI SFTP connection

    An EDI SFTP connection is a remote SFTP server used to send and
    receive EDI documents.
    """

    _name = 'edi.connection.sftp'
    _inherit = 'edi.connection.model'
    _description = "EDI SFTP Connection"

    _BATCH_SIZE = 100

    @api.model
    def connect(self, gateway):
        """Connect to SFTP server"""
        conn = SFTPOnlyClient.from_ssh_client(gateway.ssh_connect())
        if gateway.timeout:
            conn.get_channel().settimeout(gateway.timeout)
        return closing(conn)

    @api.model
    def receive_inputs(self, conn, path, transfer):
        """Receive input attachments"""
        Attachment = self.env['ir.attachment']
        inputs = Attachment.browse()
        attachment_data = []

        # List remote directory
        min_date = datetime.now() - timedelta(hours=path.age_window)
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
                                  ('name', '=', dirent.filename),
                                  ('file_size', '=', dirent.st_size)]):
                continue

            # Receive file
            filepath = os.path.join(path.path, dirent.filename)
            _logger.info("%s receiving %s", transfer.gateway_id.name,
                         filepath)
            data = conn.file(filepath, mode='rb').read()

            # Create new attachment for received file
            attachment_data.append({
                "name": dirent.filename,
                "datas": base64.b64encode(data),
                "res_model": "edi.document",
                "res_field": "input_ids",
            })

            # attachment.file_size b64decodes datas and gets the length
            attachment_size = len(data)

            # Check received size
            if attachment_size != dirent.st_size:
                raise ValidationError(
                    _("File size mismatch (expected %d got %d)") %
                    (dirent.st_size, attachment_size)
                )

        for _r, batch in batched(attachment_data, self._BATCH_SIZE):
            inputs += Attachment.create(batch)

        return inputs

    @api.model
    def send_outputs(self, conn, path, transfer):
        """Send output attachments"""
        Document = self.env['edi.document']
        Attachment = self.env['ir.attachment']
        Transfer = self.env['edi.transfer']
        outputs = Attachment.browse()
        sent = Attachment.browse()

        # Get names and sizes of existing files
        files = {x.filename: x.st_size for x in conn.listdir_attr(path.path)}

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

        # Send attachments
        for attachment in docs.mapped('output_ids').sorted('id'):

            # Skip files not matching glob pattern
            if not fnmatch.fnmatch(attachment.name, path.glob):
                continue

            # Skip files already existing in remote directory
            if attachment.name in files:
                # Assume that a file size check is sufficient to
                # identify duplicate files.  We cannot sensibly check
                # the timestamp since there is no guarantee that local
                # and remote clocks remain in sync (or in the same
                # time zone), and we cannot use checksums without
                # retrieving the potential duplicate file (which may
                # not be possible due to access restrictions).
                if attachment.file_size == files[attachment.name]:
                    continue

            # Skip files already sent, if applicable
            if not transfer.gateway_id.resend and attachment in sent:
                continue

            # Send file with temporary filename
            temppath = os.path.join(path.path, ('.%s~' % uuid.uuid4().hex))
            filepath = os.path.join(path.path, attachment.name)
            _logger.info("%s sending %s", transfer.gateway_id.name, filepath)
            data = base64.b64decode(attachment.datas)
            conn.file(temppath, mode='wb').write(data)

            # Rename temporary file
            conn.rename(temppath, filepath)

            # Record output as sent
            outputs += attachment

        return outputs
