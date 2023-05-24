"""EDI issue tracking"""

import traceback
import logging
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class Project(models.Model):
    """Extend ``project.project`` to include EDI information"""

    _inherit = 'project.project'

    use_edi_fields = fields.Boolean(string="Use EDI Fields", default=False)


class ProjectTask(models.Model):
    """Extend ``project.task`` to include EDI information"""

    _inherit = 'project.task'

    use_edi_fields = fields.Boolean(related='project_id.use_edi_fields',
                                    readonly=True)
    edi_doc_id = fields.Many2one('edi.document', string="EDI Document",
                                 index=True, ondelete='cascade')
    edi_gateway_id = fields.Many2one('edi.gateway', string="EDI Gateway",
                                     index=True, ondelete='cascade')
    edi_transfer_id = fields.Many2one('edi.transfer', string="EDI Transfer",
                                      index=True, ondelete='cascade')


class BaseIssue(models.AbstractModel):
    """Base Issue-Tracked Object"""

    # To consider: Would be good to move this abstract class in a module that only depends
    # on project module in the future. So if we want to replicate this solution not to depend on
    # EDI module by force.
    _name = "base.issues"
    _inherit = "mail.thread"
    _description = "Base Issue Object"

    # Empty list variable, will be overriden in the specific models where used.
    ISSUES_FIELD_MAP = []

    issue_ids = fields.One2many(
        "project.task",
        string="Issues",
        domain=["|", ("stage_id.fold", "=", False), ("stage_id", "=", False)],
    )
    issue_count = fields.Integer(string="Issue Count", compute="_compute_issue_counts", store=True)
    rel_issue_count = fields.Integer(
        string="Related Issue Count", compute="_compute_issue_counts", store=True
    )

    @api.model
    def display_issue_counts_depends(self):
        """
        Base fields which _compute_issue_counts depends on, it will be extended with super call
        on specific models where used.
        """
        return ["issue_ids", "issue_ids.stage_id"]

    @api.depends(lambda self: self.display_issue_counts_depends())
    def _compute_issue_counts(self):
        """Compute number of open issues (for UI display)"""
        inverse = self._fields["issue_ids"].inverse_name
        related = [
            base_field
            for field, base_field in self.ISSUES_FIELD_MAP
            if base_field != inverse and field not in self._fields
        ]
        for issues in self:
            issues.issue_count = len(
                issues.issue_ids.filtered(lambda x: all(not getattr(x, f) for f in related))
            )
            issues.rel_issue_count = len(issues.issue_ids) - issues.issue_count

    @api.multi
    def _issue_vals(self):
        """Construct values for corresponding issues"""
        self.ensure_one()
        vals = {'project_id': self.project_id.id}
        vals[self._fields['issue_ids'].inverse_name] = self.id
        for field, base_field in self.ISSUES_FIELD_MAP:
            if hasattr(self, field):
                rec = getattr(self, field)
                if rec:
                    vals[base_field] = rec.id
        return vals

    @api.multi
    def raise_issue(self, fmt, err):
        """Raise issue via issue tracker

        Raise an issue in the associated issue tracker.
        """
        self.ensure_one()

        # Parse exception
        title = err.name if isinstance(err, UserError) else str(err)
        tbe = traceback.TracebackException.from_exception(err)

        # Construct issue
        vals = self._issue_vals()
        vals['name'] = ("[%s] %s" % (self.name, title))
        issue = self.env['project.task'].create(vals)

        # Construct list of threads
        threads = [self]
        for field, _issue_field in self.ISSUES_FIELD_MAP:
            if field in self._fields:
                thread = getattr(self, field)
                if thread:
                    threads += thread

        # Add traceback if applicable
        trace = ''.join(tbe.format())
        _logger.error(trace)
        if not isinstance(err, UserError):
            issue.message_post(body=trace, content_subtype='plaintext')
            for thread in threads:
                thread.sudo().message_post(body=trace,
                                           content_subtype='plaintext')

        # Add summary
        for thread in threads:
            thread.sudo().message_post(body=(fmt % title),
                                       content_subtype='plaintext')
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
        action = self.env.ref('project.action_view_task').read()[0]
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


class EdiIssue(models.AbstractModel):
    """EDI Issue-Tracked Object

    EDI errors are raised in an issue tracker (and logged as messages
    on the originating object).
    """

    _name = "edi.issues"
    _inherit = "base.issues"
    _description = "EDI Issue-Tracked Object"

    # Mapping fields from models where issues can be created into a class attribute.
    # Class attribute is used when raising a new issue, computing issue counts and creating values
    # of issues depending on the model that the issue is being created from.
    ISSUES_FIELD_MAP = [
        (field, ("edi_%s" % field)) for field in ("doc_id", "gateway_id", "transfer_id")
    ]

    def _default_project_id(self):
        return self.env.ref("edi.project_default")

    project_id = fields.Many2one(
        "project.project", string="Issue Tracker", required=True, default=_default_project_id
    )

    def display_issue_counts_depends(self):
        # Extend with super display_issue_counts_depends defined in base.issues model
        # by adding specific edi fields that _compute_issue_counts method depends on.
        result = super().display_issue_counts_depends()
        return result + [
            "issue_ids.edi_doc_id",
            "issue_ids.edi_gateway_id",
            "issue_ids.edi_transfer_id",
        ]
