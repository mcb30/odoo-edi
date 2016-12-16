from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _
import traceback

import logging
_logger = logging.getLogger(__name__)

EDI_FIELD_MAP = [(field, ('edi_%s' % field))
                 for field in 'doc_id', 'gateway_id', 'transfer_id']


class Project(models.Model):

    _inherit = 'project.project'

    use_edi_fields = fields.Boolean(string='Use EDI Fields', default=False)


class ProjectIssue(models.Model):

    _inherit = 'project.issue'

    use_edi_fields = fields.Boolean(related='project_id.use_edi_fields')
    edi_doc_id = fields.Many2one('edi.document', string='EDI Document',
                                 index=True, ondelete='cascade')
    edi_gateway_id = fields.Many2one('edi.gateway', string='EDI Gateway',
                                index=True, ondelete='cascade')
    edi_transfer_id = fields.Many2one('edi.transfer', string='EDI Transfer',
                                      index=True, ondelete='cascade')


class EdiIssue(models.AbstractModel):
    """EDI Issue-Tracked Object

    EDI errors are raised in an issue tracker (and logged as messages
    on the originating object).
    """

    _name = 'edi.issues'
    _description = 'EDI Issue-Tracked Object'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    def _default_project_id(self):
        return self.env.ref('edi.project_default')

    project_id = fields.Many2one('project.project', string='Issue Tracker',
                                 required=True, default=_default_project_id)
    issue_ids = fields.One2many('project.issue', string='Issues',
                                domain=['|', ('stage_id.fold', '=', False),
                                             ('stage_id', '=', False)])
    issue_count = fields.Integer(string='Issue Count',
                                 compute='_compute_issue_counts', store=True)
    rel_issue_count = fields.Integer(string='Related Issue Count',
                                     compute='_compute_issue_counts',
                                     store=True)

    @api.multi
    @api.depends('issue_ids', 'issue_ids.stage_id', 'issue_ids.stage_id.fold',
                 'issue_ids.edi_doc_id', 'issue_ids.edi_gateway_id',
                 'issue_ids.edi_transfer_id')
    def _compute_issue_counts(self):
        """Compute number of open issues (for UI display)"""
        inverse = self._fields['issue_ids'].inverse_name
        related = [edi_field
                   for field, edi_field in EDI_FIELD_MAP
                   if edi_field != inverse and field not in self._fields]
        for issues in self:
            issues.issue_count = len(issues.issue_ids.filtered(
                lambda x: all(not getattr(x, f) for f in related)
                ))
            issues.rel_issue_count = (len(issues.issue_ids) -
                                      issues.issue_count)

    @api.model
    def _needaction_domain_get(self):
        """Compute domain to filter records requiring an action"""
        return [('issue_count', '!=', 0)]

    @api.multi
    def _issue_vals(self):
        """Construct values for corresponding issues"""
        self.ensure_one()
        vals = {'project_id': self.project_id.id}
        vals[self._fields['issue_ids'].inverse_name] = self.id
        for field, edi_field in EDI_FIELD_MAP:
            if hasattr(self, field):
                rec = getattr(self, field)
                if rec:
                    vals[edi_field] = rec.id
        return vals

    @api.multi
    def raise_issue(self, fmt, type, err, tb):
        """Raise issue via issue tracker

        Raise an issue in the associated issue tracker.
        """
        self.ensure_one()

        # Parse exception
        args = list(err.args)
        title = str(args[0] or err)
        detail = '\n'.join([str(x) for x in args if x])

        # Construct issue
        vals = self._issue_vals()
        vals['name'] = ('[%s] %s' % (self.name, title))
        issue = self.env['project.issue'].create(vals)

        # Add traceback if applicable
        trace = '\n'.join(traceback.format_exception(type, err, tb))
        _logger.error(trace)
        if not isinstance(err, UserError):
            issue.message_post(body=trace, content_subtype='plaintext')
            self.message_post(body=trace, content_subtype='plaintext')

        # Add detail if applicable
        if detail:
            issue.message_post(body=detail, content_subtype='plaintext')

        self.message_post(body=(fmt % title), content_subtype='plaintext')
        return issue

    @api.multi
    def close_issues(self):
        """Close all open issues"""
        for issue in self.mapped('issue_ids'):
            closed = issue.stage_find(issue.project_id.id,
                                      [('fold', '=', True)])
            issue.stage_id = closed

    @api.multi
    def action_view_issues(self):
        """View open issues"""
        self.ensure_one()
        action = self.env.ref('project_issue.action_view_issues').read()[0]
        action['domain'] = [(self._fields['issue_ids'].inverse_name,
                             '=', self.id)]
        action['context'] = {'default_%s' % k: v
                             for k, v in self._issue_vals().items()}
        action['context'].update({'create': True})
        return action

    @api.multi
    def action_close_issues(self):
        """Close all open issues"""
        self.close_issues()
        return True
