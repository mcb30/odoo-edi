from contextlib import closing
import sys
import base64
import logging
import paramiko
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

SSH_KNOWN_HOSTS = 'known_hosts'


class ir_cron(models.Model):

    _inherit = 'ir.cron'

    # This field is referenced by edi.gateway, but does not exist in
    # Odoo 10.0 and earlier.  Ensure that the field exists to allow
    # for a smoother upgrade path.
    res_id = fields.Integer()


class EdiAutoAddHostKeyPolicy(paramiko.MissingHostKeyPolicy):
    """Paramiko policy to auto-add host key to EDI Gateway"""

    def __init__(self, gw):
        self.gw = gw

    def missing_host_key(self, client, hostname, key):
        if self.gw.ssh_host_key:
            # Verify host key
            line = base64.b64decode(self.gw.ssh_host_key)
            entry = paramiko.hostkeys.HostKeyEntry.from_line(line)
            if hostname not in entry.hostnames or key != entry.key:
                raise paramiko.BadHostKeyException(hostname, key, entry.key)
        else:
            # Auto-add host key
            entry = paramiko.hostkeys.HostKeyEntry([hostname], key)
            line = entry.to_line()
            self.gw.ssh_host_key = base64.b64encode(line)
            self.gw.ssh_host_key_filename = SSH_KNOWN_HOSTS
            self.gw.message_post(body=(_('Added host key for "%s" (%s)') %
                                       (self.gw.server,
                                        self.gw.ssh_host_fingerprint)))
            _logger.warning('Added host key for "%s" (%s)',
                            self.gw.server, self.gw.ssh_host_fingerprint)


class EdiPath(models.Model):
    """EDI Path

    An EDI Path is a path to a directory on a remote file server used
    to send and/or receive EDI documents.
    """

    _name = 'edi.gateway.path'
    _description = 'EDI Gateway Path'
    _order = 'gateway_id, sequence, id'

    # Basic fields
    name = fields.Char(string='Name', required=True, index=True)
    sequence = fields.Integer(string='Sequence', help='Processing Order')
    gateway_id = fields.Many2one('edi.gateway', string='Gateway',
                                 required=True, index=True, ondelete='cascade')
    path = fields.Char(string='Directory Path', required=True)

    # Filtering
    allow_receive = fields.Boolean(string='Receive Inputs', required=True,
                                   default=True)
    allow_send = fields.Boolean(string='Send Outputs', required=True,
                                default=True)
    glob = fields.Char(string='Filename Pattern', required=True, default='*')
    age_window = fields.Float(string='Age Window (in hours)', required=True,
                              default=24)
    doc_type_ids = fields.Many2many('edi.document.type',
                                    string='Document Types')


class EdiGateway(models.Model):
    """EDI Gateway

    An EDI Gateway is a remote file server used to send and/or receive
    EDI documents.
    """

    _name = 'edi.gateway'
    _description = 'EDI Gateway'
    _inherit = ['edi.issues', 'mail.thread']

    # Basic fields
    name = fields.Char(string='Name', required=True, index=True)
    model_id = fields.Many2one('ir.model', string='Connection Model',
                               domain=['|',
                                       ('model', '=like', 'edi.connection.%'),
                                       ('model', '=like',
                                        '%.edi.connection.%')],
                               required=True, index=True)
    can_initiate = fields.Boolean(string='Initiate Connections',
                                  compute='_compute_can_initiate')
    server = fields.Char(string='Server Address')
    timeout = fields.Float(string='Timeout (in seconds)')

    # Authentication
    username = fields.Char(string='Username')
    password = fields.Char(string='Password', invisible=True, copy=False)
    ssh_host_key = fields.Binary(string='SSH Host Key')
    ssh_host_key_filename = fields.Char(default=SSH_KNOWN_HOSTS)
    ssh_host_fingerprint = fields.Char(string='SSH Host Fingerprint',
                                       readonly=True, store=True,
                                       compute='_compute_ssh_host_fingerprint')

    # Issue tracking used for asynchronously reporting errors
    issue_ids = fields.One2many(inverse_name='edi_gateway_id')

    # Paths
    path_ids = fields.One2many('edi.gateway.path', 'gateway_id',
                               string='Paths')
    path_count = fields.Integer(string='Path Count',
                                compute='_compute_path_count')

    # Transfers
    transfer_ids = fields.One2many('edi.transfer', 'gateway_id',
                                   string='Transfers')
    transfer_count = fields.Integer(string='Transfer Count',
                                    compute='_compute_transfer_count')
    last_transfer_id = fields.Many2one('edi.transfer', string='Last Transfer',
                                       readonly=True, copy=False)

    # Documents
    doc_ids = fields.One2many('edi.document', 'gateway_id',
                              string='Documents', readonly=True)
    doc_count = fields.Integer(string='Document Count',
                               compute='_compute_doc_count')

    # Scheduled jobs
    cron_ids = fields.One2many('ir.cron', 'res_id',
                               domain=[('model', '=', 'edi.gateway'),
                                       ('function', '=', 'action_transfer')],
                               string='Schedule')
    cron_count = fields.Integer(string='Schedule Count',
                                compute='_compute_cron_count')

    @api.multi
    @api.depends('model_id')
    def _compute_can_initiate(self):
        """Compute ability to initiate connections"""
        for gw in self.filtered('model_id'):
            Model = self.env[gw.model_id.model]
            gw.can_initiate = hasattr(Model, 'connect')

    @api.multi
    @api.depends('path_ids')
    def _compute_path_count(self):
        """Compute number of paths (for UI display)"""
        for gw in self:
            gw.path_count = len(gw.path_ids)

    @api.multi
    @api.depends('transfer_ids')
    def _compute_transfer_count(self):
        """Compute number of transfers (for UI display)"""
        for gw in self:
            gw.transfer_count = len(gw.transfer_ids)

    @api.multi
    @api.depends('doc_ids')
    def _compute_doc_count(self):
        """Compute number of documents (for UI display)"""
        for gw in self:
            gw.doc_count = len(gw.doc_ids)

    @api.multi
    @api.depends('cron_ids')
    def _compute_cron_count(self):
        """Compute number of scheduled jobs (for UI display)"""
        for gw in self:
            gw.cron_count = len(gw.cron_ids)

    @api.multi
    @api.depends('ssh_host_key')
    def _compute_ssh_host_fingerprint(self):
        """Compute SSH host key fingerprint"""
        for gw in self:
            if gw.ssh_host_key:
                line = base64.b64decode(gw.ssh_host_key)
                entry = paramiko.hostkeys.HostKeyEntry.from_line(line)
                digest = entry.key.get_fingerprint()
                gw.ssh_host_fingerprint = (':'.join(x.encode('hex')
                                                    for x in digest))
            else:
                gw.ssh_host_fingerprint = None

    @api.multi
    def ssh_connect(self):
        """Connect to SSH server"""
        self.ensure_one()
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(EdiAutoAddHostKeyPolicy(self))
            kwargs = {}
            if self.username:
                kwargs['username'] = self.username
            if self.password:
                kwargs['password'] = self.password
            if self.timeout:
                kwargs['timeout'] = self.timeout
                kwargs['banner_timeout'] = self.timeout
            ssh.connect(self.server, **kwargs)
        except paramiko.SSHException as e:
            raise UserError(e.message)
        return ssh

    @api.multi
    def lock_for_transfer(self, transfer):
        """Lock gateway for transfer"""
        # Update a single field on the gateway.  This implicitly
        # acquires a FOR UPDATE lock on the gateway's table row, and
        # so functions as an advisory lock on the gateway for the
        # remainder of the transaction.
        self.write({'last_transfer_id': transfer.id})

    @api.multi
    def action_view_paths(self):
        """View paths"""
        self.ensure_one()
        action = self.env.ref('edi.gateway_path_action').read()[0]
        action['domain'] = [('gateway_id', '=', self.id)]
        action['context'] = {'default_gateway_id': self.id}
        return action

    @api.multi
    def action_view_transfers(self):
        """View transfers"""
        self.ensure_one()
        action = self.env.ref('edi.transfer_action').read()[0]
        action['domain'] = [('gateway_id', '=', self.id)]
        return action

    @api.multi
    def action_view_docs(self):
        """View documents"""
        self.ensure_one()
        action = self.env.ref('edi.document_action').read()[0]
        action['domain'] = [('gateway_id', '=', self.id)]
        action['context'] = {'create': False}
        return action

    @api.multi
    def action_view_cron(self):
        """View scheduled jobs"""
        self.ensure_one()
        action = self.env.ref('edi.cron_action').read()[0]
        action['domain'] = [('model', '=', 'edi.gateway'),
                            ('function', '=', 'action_transfer'),
                            ('res_id', '=', self.id)]
        action['context'] = {'default_model': 'edi.gateway',
                             'default_function': 'action_transfer',
                             'default_res_id': self.id,
                             'create': True}
        return action

    @api.multi
    def action_test(self):
        """Test connection"""
        self.ensure_one()
        Model = self.env[self.model_id.model]
        try:
            with closing(Model.connect(self)) as _conn:
                pass
        except Exception as err:
            self.raise_issue(_('Connection test failed: %s'), *sys.exc_info())
            return False
        self.message_post(body=_('Connection tested successfully'))
        return True

    @api.multi
    def do_transfer(self, conn=None):
        """Receive input attachments, process documents, send outputs"""
        self.ensure_one()
        transfer = self.transfer_ids.create({'gateway_id': self.id})
        self.lock_for_transfer(transfer)
        Model = self.env[self.model_id.model]
        try:
            if conn:
                transfer.do_transfer(conn)
            else:
                with closing(Model.connect(self)) as conn:
                    transfer.do_transfer(conn)
        except Exception as err:
            transfer.raise_issue(_('Transfer failed: %s'), *sys.exc_info())
        return transfer

    @api.multi
    def action_transfer(self):
        """Receive input attachments, process documents, send outputs"""
        self.ensure_one()
        transfer = self.do_transfer()
        return not transfer.issue_ids

    @api.multi
    def xmlrpc_transfer(self, **kwargs):
        """Receive input attachments, process documents, send outputs"""
        self = self or self.env.ref('edi.gateway_xmlrpc')
        self.ensure_one()
        conn = dict(**kwargs)
        transfer = self.do_transfer(conn=conn)
        conn['docs'] = [{'id': x.id, 'name': x.name, 'state': x.state}
                        for x in transfer.doc_ids]
        if transfer.issue_ids:
            conn['errors'] = [{'id': x.id, 'name': x.name}
                              for x in transfer.issue_ids]
        return conn
