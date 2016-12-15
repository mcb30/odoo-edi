from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _
import sys
import base64

import logging
_logger = logging.getLogger(__name__)


class EdiDocumentType(models.Model):
    """EDI document type

    An EDI document type comprises a set of associated EDI record
    types and a model used for parsing attachments into lists of EDI
    records.

    For example: an EDI Product Master Data document type may comprise
    a single associated EDI Product record type and a model capable of
    parsing a custom CSV formatted attachment into a list of EDI
    Product records.
    """

    _name = 'edi.document.type'
    _description = 'EDI Document Type'
    _order = 'sequence, id'

    def _default_sequence_id(self):
        return self.env.ref('edi.sequence_default')

    def _default_project_id(self):
        return self.env.ref('edi.project_default')

    # Basic fields
    name = fields.Char(string='Name', required=True, index=True)
    model_id = fields.Many2one('ir.model', string='Document Model',
                               domain=[('model', '!=', 'edi.document.type'),
                                       '|',
                                       ('model', '=like', 'edi.document.%'),
                                       ('model', '=like', '%.edi.document.%')],
                               required=True, index=True)
    rec_type_ids = fields.Many2many('edi.record.type', string='Record Types')

    # Autodetection order when detecting a document type based upon
    # the set of input attachments.
    sequence = fields.Integer(string='Sequence', help='Autodetection Order')

    # Sequence for generating document names
    sequence_id = fields.Many2one('ir.sequence',
                                  string='Document Name Sequence',
                                  required=True, default=_default_sequence_id)

    # Issue tracker used for asynchronously reporting errors
    project_id = fields.Many2one('project.project', string='Issue Tracker',
                                 required=True, default=_default_project_id)

    _sql_constraints = [('model_uniq', 'unique (model_id)',
                         'The document model must be unique')]

    @api.multi
    def compute_use_record(self, field, model):
        """Compute use of record type"""
        for doc_type in self:
            rec_models = doc_type.mapped('rec_type_ids.model_id.model')
            setattr(doc_type, field, (model in rec_models))

    @api.model
    def autocreate(self, inputs):
        """Autocreate documents based on input attachments"""
        Document = self.env['edi.document']
        docs = Document.browse()
        for doc_type in self or self.search([]):
            Model = self.env[doc_type.model_id.model]
            if not hasattr(Model, 'autotype'):
                continue
            for consume in Model.autotype(inputs):
                doc = Document.create({'doc_type_id': doc_type.id})
                consume.write({'res_id': doc.id})
                inputs -= consume
                docs += doc
        if inputs:
            if len(self) == 1:
                doc_type_unknown = self
            else:
                doc_type_unknown = self.env.ref('edi.document_type_unknown')
            doc = Document.create({'doc_type_id': doc_type_unknown.id})
            inputs.write({'res_id': doc.id})
            docs += doc
        return docs


class EdiDocument(models.Model):
    """EDI document

    An EDI document comprises a set of attachments and the
    corresponding set of EDI records.

    For example: an EDI Product Master Data document may comprise a
    single custom CSV formatted attachment and a set of EDI Product
    records representing the new and changed product definitions
    parsed from the CSV file.
    """

    _name = 'edi.document'
    _description = 'EDI Document'
    _inherit = ['edi.issues', 'mail.thread']

    # Basic fields
    name = fields.Char(string='Name', index=True, copy=False,
                       states={'done': [('readonly', True)],
                               'cancel': [('readonly', True)]})
    state = fields.Selection([('draft', 'New'),
                              ('cancel', 'Cancelled'),
                              ('prep', 'Prepared'),
                              ('done', 'Completed')],
                             string='Status', readonly=True, index=True,
                             default='draft', copy=False,
                             track_visibility='onchange')
    doc_type_id = fields.Many2one('edi.document.type', string='Document Type',
                                  required=True, readonly=True)
    prepare_date = fields.Datetime(string='Prepared on', readonly=True,
                                   copy=False)
    execute_date = fields.Datetime(string='Executed on', readonly=True,
                                   copy=False)
    note = fields.Text(string='Notes')

    # Communications
    transfer_id = fields.Many2one('edi.transfer', string='Transfer',
                                  readonly=True, copy=False)
    gateway_id = fields.Many2one('edi.gateway',
                                 related='transfer_id.gateway_id',
                                 readonly=True, store=True, copy=False)

    # Attachments (e.g. CSV files)
    input_ids = fields.One2many('ir.attachment', 'res_id',
                                domain=[('res_model', '=', 'edi.document'),
                                        ('res_field', '=', 'input_ids')],
                                string='Input Attachments')
    output_ids = fields.One2many('ir.attachment', 'res_id',
                                 domain=[('res_model', '=', 'edi.document'),
                                         ('res_field', '=', 'output_ids')],
                                 string='Output Attachments')
    input_count = fields.Integer(string='Input Count',
                                 compute='_compute_input_count', store=True)
    output_count = fields.Integer(string='Output Count',
                                  compute='_compute_output_count', store=True)

    # Issues (i.e. asynchronously reported errors)
    project_id = fields.Many2one(related='doc_type_id.project_id')
    issue_ids = fields.One2many(inverse_name='edi_doc_id')

    @api.depends('input_ids', 'input_ids.res_id')
    def _compute_input_count(self):
        """Compute number of input attachments (for UI display)"""
        for doc in self:
            doc.input_count = len(doc.input_ids)

    @api.depends('output_ids', 'output_ids.res_id')
    def _compute_output_count(self):
        """Compute number of output attachments (for UI display)"""
        for doc in self:
            doc.output_count = len(doc.output_ids)

    @api.multi
    def _get_state_name(self):
        """Get name of current state"""
        vals = dict(self.fields_get(allfields=['state'])['state']['selection'])
        return vals[self.state]

    @api.model
    def create(self, vals):
        """Create record (generating name automatically if needed)"""
        doc = super(EdiDocument, self).create(vals)
        if not doc.name:
            doc.name = doc.doc_type_id.sequence_id.next_by_id()
        return doc

    @api.multi
    def copy(self, default=None):
        """Duplicate record (including input attachments)"""
        self.ensure_one()
        new = super(EdiDocument, self).copy(default)
        for attachment in self.input_ids:
            attachment.copy({
                'res_id': new.id,
                'datas': attachment.datas,
                })
        return new

    @api.multi
    def execute_records(self):
        """Execute records"""
        self.ensure_one()
        for rec_type in self.doc_type_id.rec_type_ids:
            RecModel = self.env[rec_type.model_id.model]
            RecModel.search([('doc_id', '=', self.id)]).execute()

    @api.multi
    def action_prepare(self):
        """Prepare document

        Parse input attachments and create corresponding EDI records.
        """
        self.ensure_one()
        # Check document state
        if self.state != 'draft':
            raise UserError(_('Cannot prepare a %s document') %
                            self._get_state_name())
        # Close any stale issues
        self.close_issues()
        # Create audit trail
        Audit = self.env['edi.attachment.audit']
        Audit.audit_attachments(self, self.input_ids,
                                body=_('Input attachments'))
        # Prepare document
        DocModel = self.env[self.doc_type_id.model_id.model]
        try:
            with self.env.cr.savepoint():
                DocModel.prepare(self)
        except Exception as e:
            self.raise_issue(_('Preparation failed: %s'), *sys.exc_info())
            return False
        # Mark as prepared
        self.prepare_date = fields.Datetime.now()
        self.state = 'prep'
        return True

    @api.multi
    def action_unprepare(self):
        """Return Prepared document to Draft state"""
        self.ensure_one()
        # Check document state
        if self.state != 'prep':
            raise UserError(_('Cannot unprepare a %s document') %
                            self._get_state_name())
        # Close any stale issues
        self.close_issues()
        # Delete any records
        for rec_type in self.doc_type_id.rec_type_ids.sorted(reverse=True):
                Model = self.env[rec_type.model_id.model]
                Model.search([('doc_id', '=', self.id)]).unlink()
        # Mark as in draft
        self.prepare_date = None
        self.state = 'draft'
        return True

    @api.multi
    def action_execute(self):
        """Execute document

        Parse EDI records and update database.
        """
        self.ensure_one()
        # Check document state
        if self.state != 'prep':
            raise UserError(_('Cannot execute a %s document') %
                            self._get_state_name())
        # Close any stale issues
        self.close_issues()
        # Execute document
        DocModel = self.env[self.doc_type_id.model_id.model]
        try:
            with self.env.cr.savepoint():
                if hasattr(DocModel, 'execute'):
                    # Use custom document execution method, if applicable
                    DocModel.execute(self)
                else:
                    # Otherwise, execute all records
                    self.execute_records()
        except Exception as e:
            self.raise_issue(_('Execution failed: %s'), *sys.exc_info())
            return False
        # Create audit trail
        Audit = self.env['edi.attachment.audit']
        Audit.audit_attachments(self, self.output_ids,
                                body=_('Output attachments'))
        # Mark as processed
        self.execute_date = fields.Datetime.now()
        self.state = 'done'
        return True

    @api.multi
    def action_cancel(self):
        """Cancel document"""
        self.ensure_one()
        # Check document state
        if self.state == 'done':
            raise UserError(_('Cannot cancel a %s document') %
                            self._get_state_name())
        # Close any stale issues
        self.close_issues()
        # Mark as cancelled
        self.state = 'cancel'
        return True

    @api.multi
    def action_view_inputs(self):
        """View input attachments"""
        self.ensure_one()
        action = self.env.ref('edi.document_attachments_action').read()[0]
        action['display_name'] = _('Inputs')
        action['domain'] = [('res_model', '=', 'edi.document'),
                            ('res_field', '=', 'input_ids'),
                            ('res_id', '=', self.id)]
        action['context'] = {'default_res_model': 'edi.document',
                             'default_res_field': 'input_ids',
                             'default_res_id': self.id}
        return action

    @api.multi
    def action_view_outputs(self):
        """View output attachments"""
        self.ensure_one()
        action = self.env.ref('edi.document_attachments_action').read()[0]
        action['display_name'] = _('Outputs')
        action['domain'] = [('res_model', '=', 'edi.document'),
                            ('res_field', '=', 'output_ids'),
                            ('res_id', '=', self.id)]
        action['context'] = {'default_res_model': 'edi.document',
                             'default_res_field': 'output_ids',
                             'default_res_id': self.id}
        return action


class EdiUnknownDocument(models.AbstractModel):

    _name = 'edi.document.unknown'
    _description = 'Unknown Document'

    @api.model
    def prepare(self, doc):
        raise UserError(_('Unknown document type'))
