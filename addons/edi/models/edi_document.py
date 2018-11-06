"""EDI documents"""

from base64 import b64decode, b64encode
from collections import namedtuple
import logging
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

AutodetectDocument = namedtuple('AutodetectDocument', ['type', 'inputs'])


class IrModel(models.Model):
    """Extend ``ir.model`` to include EDI information"""

    _inherit = 'ir.model'

    is_edi_document = fields.Boolean(string="EDI Document Model", default=False,
                                     help="This is an EDI document model")

    def _reflect_model_params(self, model):
        vals = super()._reflect_model_params(model)
        vals['is_edi_document'] = (
            model._name != 'edi.document.model' and
            issubclass(type(model), self.pool['edi.document.model'])
        )
        return vals


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
    _description = "EDI Document Type"
    _order = 'sequence, id'

    def _default_sequence_id(self):
        return self.env.ref('edi.sequence_default')

    def _default_project_id(self):
        return self.env.ref('edi.project_default')

    # Basic fields
    name = fields.Char(string="Name", required=True, index=True)
    model_id = fields.Many2one('ir.model', string="Document Model",
                               domain=[('is_edi_document', '=', True)],
                               required=True, index=True)
    rec_type_ids = fields.Many2many('edi.record.type', string="Record Types")

    # Autodetection order when detecting a document type based upon
    # the set of input attachments.
    sequence = fields.Integer(string="Sequence", help="Autodetection Order")

    # Sequence for generating document names
    sequence_id = fields.Many2one('ir.sequence',
                                  string="Document Name Sequence",
                                  required=True, default=_default_sequence_id)

    # Issue tracker used for asynchronously reporting errors
    project_id = fields.Many2one('project.project', string="Issue Tracker",
                                 required=True, default=_default_project_id)

    _sql_constraints = [('model_uniq', 'unique (model_id)',
                         "The document model must be unique")]

    @api.model
    def autocreate(self, inputs):
        """Autocreate documents based on input attachments"""
        Document = self.env['edi.document']
        inputs.write({
            'res_model': 'edi.document',
            'res_field': 'input_ids',
        })
        input_ids = inputs.ids
        autodetects = []
        for doc_type in self or self.search([]):
            Model = self.env[doc_type.model_id.model]
            if not hasattr(Model, 'autotype'):
                continue
            for consume in Model.autotype(inputs):
                autodetects.append(AutodetectDocument(doc_type, consume))
                inputs -= consume
        if inputs:
            if len(self) == 1:
                doc_type_unknown = self
            else:
                doc_type_unknown = self.env.ref('edi.document_type_unknown')
            autodetects.append(AutodetectDocument(doc_type_unknown, inputs))
        docs = Document.browse()
        by_first_input = lambda x: input_ids.index(min(x.inputs.ids))
        for autodetect in sorted(autodetects, key=by_first_input):
            doc = Document.create({'doc_type_id': autodetect.type.id})
            autodetect.inputs.write({'res_id': doc.id})
            docs += doc
        return docs

    @api.multi
    def autoemit(self):
        """Create, prepare, and execute documents with no inputs"""
        Document = self.env['edi.document']
        docs = Document.browse()
        for doc_type in self:
            doc = Document.create({'doc_type_id': doc_type.id})
            doc.action_execute()
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
    _description = "EDI Document"
    _inherit = ['edi.issues', 'mail.thread']

    # Basic fields
    name = fields.Char(string="Name", index=True, copy=False,
                       states={'done': [('readonly', True)],
                               'cancel': [('readonly', True)]})
    state = fields.Selection([('draft', "New"),
                              ('cancel', "Cancelled"),
                              ('prep', "Prepared"),
                              ('done', "Completed")],
                             string="Status", readonly=True, index=True,
                             default='draft', copy=False,
                             track_visibility='onchange')
    doc_type_id = fields.Many2one('edi.document.type', string="Document Type",
                                  required=True, readonly=True, index=True)
    prepare_date = fields.Datetime(string="Prepared on", readonly=True,
                                   copy=False)
    execute_date = fields.Datetime(string="Executed on", readonly=True,
                                   copy=False)
    note = fields.Text(string="Notes")

    # Communications
    transfer_id = fields.Many2one('edi.transfer', string="Transfer",
                                  readonly=True, copy=False, index=True)
    gateway_id = fields.Many2one('edi.gateway',
                                 related='transfer_id.gateway_id',
                                 readonly=True, store=True, copy=False,
                                 index=True)

    # Attachments (e.g. CSV files)
    input_ids = fields.One2many('ir.attachment', 'res_id',
                                domain=[('res_model', '=', 'edi.document'),
                                        ('res_field', '=', 'input_ids')],
                                string="Input Attachments")
    output_ids = fields.One2many('ir.attachment', 'res_id',
                                 domain=[('res_model', '=', 'edi.document'),
                                         ('res_field', '=', 'output_ids')],
                                 string="Output Attachments")
    input_count = fields.Integer(string="Input Count",
                                 compute='_compute_input_count', store=True)
    output_count = fields.Integer(string="Output Count",
                                  compute='_compute_output_count', store=True)

    # Issues (i.e. asynchronously reported errors)
    project_id = fields.Many2one(related='doc_type_id.project_id')
    issue_ids = fields.One2many(inverse_name='edi_doc_id')

    # Record type names (solely for use by views)
    rec_type_names = fields.Char(string="Record Type Names",
                                 compute='_compute_rec_type_names')

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
    @api.depends('doc_type_id', 'doc_type_id.rec_type_ids',
                 'doc_type_id.rec_type_ids.model_id',
                 'doc_type_id.rec_type_ids.model_id.model')
    def _compute_rec_type_names(self):
        """Compute record type name list

        The record type name list is used by the view definitions to
        determine whether or not to display particular record-specific
        pages within the document form view.

        This avoids the need for each record type to define a custom
        boolean field on ``edi.document.type`` to convey the same
        information.

        Note that this hack would be entirely unnecessary if the Odoo
        domain syntax allowed us to express the concept of "visible if
        ``rec_type_ids`` contains <value>".
        """
        for doc in self:
            rec_models = doc.mapped('doc_type_id.rec_type_ids.model_id.model')
            doc.rec_type_names = '/%s/' % '/'.join(rec_models)

    @api.multi
    def _get_state_name(self):
        """Get name of current state"""
        vals = dict(self.fields_get(allfields=['state'])['state']['selection'])
        return vals[self.state]

    @api.model
    def create(self, vals):
        """Create record (generating name automatically if needed)"""
        doc = super().create(vals)
        if not doc.name:
            doc.name = doc.doc_type_id.sequence_id.next_by_id()
        return doc

    @api.multi
    def copy(self, default=None):
        """Duplicate record (including input attachments)"""
        self.ensure_one()
        new = super().copy(default)
        for attachment in self.input_ids.sorted('id'):
            attachment.copy({
                'res_id': new.id,
                'datas': attachment.datas,
            })
        return new

    @api.multi
    def lock_for_action(self):
        """Lock document"""
        for doc in self:
            # Obtain a database row-level exclusive lock by writing the record
            doc.state = doc.state

    @api.multi
    def inputs(self):
        """Iterate over decoded input attachments"""
        self.ensure_one()
        if not self.input_ids:
            raise UserError(_("Missing input attachment"))
        return ((x.datas_fname, b64decode(x.datas))
                for x in self.input_ids.sorted('id'))

    @api.multi
    def input(self):
        """Get single decoded input attachment"""
        self.ensure_one()
        if len(self.input_ids) > 1:
            raise UserError(_("More than one input attachment"))
        return next(self.inputs())

    @api.multi
    def output(self, name, data):
        """Create output attachment"""
        self.ensure_one()
        Attachment = self.env['ir.attachment']
        attachment = Attachment.create({
            'name': name,
            'datas_fname': name,
            'datas': b64encode(data),
            'res_model': 'edi.document',
            'res_field': 'output_ids',
            'res_id': self.id,
        })
        return attachment

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
        # Lock document
        self.lock_for_action()
        # Check document state
        if self.state != 'draft':
            raise UserError(_("Cannot prepare a %s document") %
                            self._get_state_name())
        # Close any stale issues
        self.close_issues()
        # Create audit trail
        Audit = self.env['edi.attachment.audit']
        Audit.audit_attachments(self, self.input_ids,
                                body=_("Input attachments"))
        # Prepare document
        _logger.info("Preparing %s", self.name)
        DocModel = self.env[self.doc_type_id.model_id.model]
        try:
            # pylint: disable=broad-except
            with self.env.cr.savepoint():
                DocModel.prepare(self)
        except Exception as err:
            self.raise_issue(_("Preparation failed: %s"), err)
            return False
        # Mark as prepared
        self.prepare_date = fields.Datetime.now()
        self.state = 'prep'
        _logger.info("Prepared %s", self.name)
        return True

    @api.multi
    def action_unprepare(self):
        """Return Prepared document to Draft state"""
        self.ensure_one()
        # Lock document
        self.lock_for_action()
        # Check document state
        if self.state != 'prep':
            raise UserError(_("Cannot unprepare a %s document") %
                            self._get_state_name())
        # Close any stale issues
        self.close_issues()
        # Delete any records
        _logger.info("Unpreparing %s", self.name)
        for rec_type in self.doc_type_id.rec_type_ids.sorted(reverse=True):
            Model = self.env[rec_type.model_id.model]
            Model.search([('doc_id', '=', self.id)]).unlink()
        # Mark as in draft
        self.prepare_date = None
        self.state = 'draft'
        _logger.info("Unprepared %s", self.name)
        return True

    @api.multi
    def action_execute(self):
        """Execute document

        Parse EDI records and update database.
        """
        self.ensure_one()
        # Lock document
        self.lock_for_action()
        # Automatically prepare document if needed
        if self.state == 'draft':
            prepared = self.action_prepare()
            if not prepared:
                return False
        # Check document state
        if self.state != 'prep':
            raise UserError(_("Cannot execute a %s document") %
                            self._get_state_name())
        # Close any stale issues
        self.close_issues()
        # Execute document
        _logger.info("Executing %s", self.name)
        DocModel = self.env[self.doc_type_id.model_id.model]
        try:
            # pylint: disable=broad-except
            with self.env.cr.savepoint():
                DocModel.execute(self)
        except Exception as err:
            self.raise_issue(_("Execution failed: %s"), err)
            return False
        # Create audit trail
        Audit = self.env['edi.attachment.audit']
        Audit.audit_attachments(self, self.output_ids,
                                body=_("Output attachments"))
        # Mark as processed
        self.execute_date = fields.Datetime.now()
        self.state = 'done'
        _logger.info("Executed %s", self.name)
        return True

    @api.multi
    def action_cancel(self):
        """Cancel document"""
        self.ensure_one()
        # Lock document
        self.lock_for_action()
        # Check document state
        if self.state == 'done':
            raise UserError(_("Cannot cancel a %s document") %
                            self._get_state_name())
        # Close any stale issues
        self.close_issues()
        # Mark as cancelled
        self.state = 'cancel'
        _logger.info("Cancelled %s", self.name)
        return True

    @api.multi
    def action_view_inputs(self):
        """View input attachments"""
        self.ensure_one()
        action = self.env.ref('edi.document_attachments_action').read()[0]
        action['display_name'] = _("Inputs")
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
        action['display_name'] = _("Outputs")
        action['domain'] = [('res_model', '=', 'edi.document'),
                            ('res_field', '=', 'output_ids'),
                            ('res_id', '=', self.id)]
        action['context'] = {'default_res_model': 'edi.document',
                             'default_res_field': 'output_ids',
                             'default_res_id': self.id}
        return action


class EdiDocumentModel(models.AbstractModel):
    """EDI document model

    This is the abstract base class for all EDI document models.
    """

    _name = 'edi.document.model'
    _description = "EDI Document Model"

    @api.model
    def record_models(self, doc, supermodel='edi.record'):
        """Get EDI record model classes"""
        doc.ensure_one()
        SuperModel = self.env[supermodel]
        return [
            self.env[x]
            for x in doc.doc_type_id.rec_type_ids.mapped('model_id.model')
            if issubclass(type(self.env[x]), type(SuperModel))
        ]

    @api.model
    def record_model(self, doc, supermodel='edi.record'):
        """Get EDI record model class"""
        Models = self.record_models(doc, supermodel=supermodel)
        if not Models:
            return None
        if len(Models) != 1:
            raise ValueError(_("Expected singleton record model: %s") %
                             ','.join(x._name for x in Models))
        return Models[0]

    @api.model
    def prepare(self, _doc):
        """Prepare document"""
        pass

    @api.model
    def execute(self, doc):
        """Execute document"""
        doc.execute_records()


class EdiDocumentUnknown(models.AbstractModel):
    """Unknown EDI document model"""

    _name = 'edi.document.unknown'
    _inherit = 'edi.document.model'
    _description = "Unknown Document"

    @api.model
    def prepare(self, doc):
        """Prepare document"""
        super().prepare(doc)
        raise UserError(_("Unknown document type"))
