"""EDI transfers"""

import logging
from odoo import api, fields, models
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class EdiTransfer(models.Model):
    """EDI Transfer

    An EDI Transfer is a single transfer (comprising zero or more
    uploads and/or downloads) with an EDI Gateway.
    """

    _name = "edi.transfer"
    _description = "EDI Transfer"
    _inherit = ["edi.issues", "mail.thread"]

    def _default_name(self):
        return fields.Datetime.now()

    # Basic fields
    name = fields.Char(string="Name", required=True, index=True, default=_default_name)
    gateway_id = fields.Many2one(
        "edi.gateway",
        string="Gateway",
        required=True,
        index=True,
        readonly=True,
        ondelete="restrict",
    )
    note = fields.Text(string="Notes")
    allow_receive = fields.Boolean(
        string="Receive Inputs", required=True, default=True, readonly=True
    )
    allow_process = fields.Boolean(
        string="Process Documents", required=True, default=True, readonly=True
    )
    allow_send = fields.Boolean(string="Send Outputs", required=True, default=True, readonly=True)

    # Associated documents and attachments
    doc_ids = fields.One2many("edi.document", "transfer_id", string="Documents", readonly=True)
    input_ids = fields.Many2many(
        "ir.attachment",
        "edi_transfer_input_ids",
        domain=[("res_model", "=", "edi.document"), ("res_field", "=", "input_ids")],
        string="Input Attachments",
        readonly=True,
    )
    output_ids = fields.Many2many(
        "ir.attachment",
        "edi_transfer_output_ids",
        domain=[("res_model", "=", "edi.document"), ("res_field", "=", "output_ids")],
        string="Output Attachments",
        readonly=True,
    )
    doc_count = fields.Integer(string="Document Count", compute="_compute_doc_count", store=True)
    input_count = fields.Integer(string="Input Count", compute="_compute_input_count", store=True)
    output_count = fields.Integer(
        string="Output Count", compute="_compute_output_count", store=True
    )

    # Issue tracking used for asynchronously reporting errors
    project_id = fields.Many2one(related="gateway_id.project_id", readonly=True)
    issue_ids = fields.One2many(inverse_name="edi_transfer_id")

    @api.depends("doc_ids")
    def _compute_doc_count(self):
        """Compute number of documents (for UI display)"""
        for xfer in self:
            xfer.doc_count = len(xfer.doc_ids)

    @api.depends("input_ids")
    def _compute_input_count(self):
        """Compute number of input attachments (for UI display)"""
        for xfer in self:
            xfer.input_count = len(xfer.input_ids)

    @api.depends("output_ids")
    def _compute_output_count(self):
        """Compute number of output attachments (for UI display)"""
        for xfer in self:
            xfer.output_count = len(xfer.output_ids)

    def action_view_docs(self):
        """View documents"""
        self.ensure_one()
        action = self.env.ref("edi.document_action").read()[0]
        action["domain"] = [("transfer_id", "=", self.id)]
        action["context"] = {"create": False}
        return action

    def action_view_inputs(self):
        """View input attachments"""
        self.ensure_one()
        action = self.env.ref("edi.document_attachments_action").read()[0]
        action["name"] = _("Inputs")
        action["domain"] = [("id", "in", self.mapped("input_ids.id"))]
        action["context"] = {"create": False}
        return action

    def action_view_outputs(self):
        """View output attachments"""
        self.ensure_one()
        action = self.env.ref("edi.document_attachments_action").read()[0]
        action["name"] = _("Outputs")
        action["domain"] = [("id", "in", self.mapped("output_ids.id"))]
        action["context"] = {"create": False}
        return action

    def receive_inputs(self, conn):
        """Receive input attachments and create documents"""
        self.ensure_one()
        Audit = self.env["edi.attachment.audit"]
        Model = self.env[self.gateway_id.model_id.model]
        for path in self.gateway_id.path_ids.filtered("allow_receive"):

            # Receive input attachments
            inputs = Model.receive_inputs(conn, path, self)
            if not inputs:
                continue

            # Log received input attachments
            Audit.audit_attachments(self, inputs, body=(_("Received %s") % path.name))

            # Associate input attachments with this transfer
            self.input_ids += inputs

            # Create documents for attachments
            docs = path.doc_type_ids.autocreate(inputs)

            # Associate documents with this transfer
            docs.write({"transfer_id": self.id})

            # Log created documents
            for doc in docs:
                Audit.audit_attachments(self, doc.input_ids, body=(_("Created %s") % doc.name))
                _logger.info(
                    "%s created %s (%s)",
                    self.gateway_id.name,
                    doc.name,
                    ", ".join(doc.mapped("input_ids.name")),
                )

    def send_outputs(self, conn):
        """Send output attachments"""
        self.ensure_one()
        Audit = self.env["edi.attachment.audit"]
        Model = self.env[self.gateway_id.model_id.model]
        for path in self.gateway_id.path_ids.filtered("allow_send"):

            # Send output attachments
            outputs = Model.send_outputs(conn, path, self)
            if not outputs:
                continue

            # Log sent attachments
            Audit.audit_attachments(self, outputs, body=(_("Sent %s") % path.name))

            # Associate output attachments with this transfer
            self.output_ids += outputs

    def do_transfer(self, conn):
        """Receive input attachments, process documents, send outputs"""
        self.ensure_one()

        # Receive inputs, if applicable
        if self.allow_receive:
            self.receive_inputs(conn)

        # Prepare and execute documents, if applicable
        if self.allow_process:
            for doc in self.doc_ids:
                _logger.info("%s preparing %s", self.gateway_id.name, doc.name)
                prepared = doc.action_prepare()
                if prepared:
                    _logger.info("%s executing %s", self.gateway_id.name, doc.name)
                    executed = doc.action_execute()
                    if executed:
                        self.message_post(body=(_("Executed %s") % doc.name))
                    else:
                        self.message_post(body=(_("Prepared %s") % doc.name))

        # Send outputs, if applicable
        if self.allow_send:
            self.send_outputs(conn)

        _logger.info("%s transfer complete", self.gateway_id.name)
