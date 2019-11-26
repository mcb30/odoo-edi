"""EDI XML-RPC connection"""

import fnmatch
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)


class EdiConnectionXMLRPC(models.AbstractModel):
    """EDI XML-RPC connection

    An EDI XML-RPC connection is initiated by external code via the
    Odoo XML-RPC interface.
    """

    _name = 'edi.connection.xmlrpc'
    _inherit = 'edi.connection.model'
    _description = "EDI XML-RPC Connection"

    @api.model
    def receive_inputs(self, conn, path, _transfer):
        """Receive input attachments"""
        Attachment = self.env['ir.attachment']
        inputs = Attachment.browse()

        # Skip non-existent paths
        if path.path not in conn:
            return

        # Create input attachments
        for f in list(conn[path.path]):

            # Skip files not matching glob pattern
            if not fnmatch.fnmatch(f['name'], path.glob):
                continue

            # Create new attachment for input file
            attachment = Attachment.create({
                'name': f['name'],
                'name': f['name'],
                'datas': str(f['data']),
                'res_model': 'edi.document',
                'res_field': 'input_ids',
            })
            inputs += attachment

            # Consume input file
            conn[path.path].remove(f)

        return inputs

    @api.model
    def send_outputs(self, conn, path, transfer):
        """Send output attachments"""

        # Skip non-existent paths
        if path.path not in conn:
            return

        # Identify documents
        docs = transfer.doc_ids
        if path.doc_type_ids:
            docs = docs.filtered(lambda x: x.doc_type_id in path.doc_type_ids)

        # Identify output attachments
        outputs = docs.mapped('output_ids').sorted('id').filtered(
            lambda x: fnmatch.fnmatch(x.name, path.glob)
        )

        # Skip files already sent, if applicable
        if not transfer.gateway_id.resend:
            outputs -= self.env['edi.transfer'].search([
                ('output_ids', 'in', outputs.ids),
                ('gateway_id', '=', transfer.gateway_id.id),
            ]).mapped('output_ids')

        # Create output files from attachments
        conn[path.path] += [{'name': x.name, 'data': x.datas}
                            for x in outputs]

        return outputs
