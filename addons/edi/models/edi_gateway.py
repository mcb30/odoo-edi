"""EDI gateway"""

import base64
import logging
import os
import paramiko
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import config
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

SSH_KNOWN_HOSTS = 'known_hosts'


class ServerActions(models.Model):
    """Add EDI Transfer option in server actions"""

    _inherit = 'ir.actions.server'

    state = fields.Selection(selection_add=[('edi', "EDI Transfer")])
    edi_gateway_id = fields.Many2one('edi.gateway', string="EDI Gateway",
                                     index=True, ondelete='cascade')

    @api.model
    def run_action_edi_multi(self, action, eval_context=None):
        """Run EDI server action"""
        # pylint: disable=unused-argument
        action.edi_gateway_id.action_transfer()


class EdiAutoAddHostKeyPolicy(paramiko.MissingHostKeyPolicy):
    """Paramiko policy to auto-add host key to EDI Gateway"""

    def __init__(self, gw):
        self.gw = gw

    def missing_host_key(self, client, hostname, key):
        if self.gw.ssh_host_key:
            # Verify host key
            line = base64.b64decode(self.gw.ssh_host_key).decode()
            entry = paramiko.hostkeys.HostKeyEntry.from_line(line)
            if hostname not in entry.hostnames or key != entry.key:
                raise paramiko.BadHostKeyException(hostname, key, entry.key)
        else:
            # Auto-add host key
            entry = paramiko.hostkeys.HostKeyEntry([hostname], key)
            line = entry.to_line()
            self.gw.ssh_host_key = base64.b64encode(line.encode())
            self.gw.ssh_host_key_filename = SSH_KNOWN_HOSTS
            self.gw.message_post(body=(_("Added host key for '%s' (%s)") %
                                       (self.gw.server,
                                        self.gw.ssh_host_fingerprint)))
            _logger.warning("Added host key for '%s' (%s)",
                            self.gw.server, self.gw.ssh_host_fingerprint)


class EdiPath(models.Model):
    """EDI Path

    An EDI Path is a path to a directory on a remote file server used
    to send and/or receive EDI documents.
    """

    _name = 'edi.gateway.path'
    _description = "EDI Gateway Path"
    _order = 'gateway_id, sequence, id'

    # Basic fields
    name = fields.Char(string="Name", required=True, index=True)
    sequence = fields.Integer(string="Sequence", help="Processing Order")
    gateway_id = fields.Many2one('edi.gateway', string="Gateway",
                                 required=True, index=True, ondelete='cascade')
    path = fields.Char(string="Directory Path", required=True)

    # Filtering
    allow_receive = fields.Boolean(string="Receive Inputs", required=True,
                                   default=True)
    allow_send = fields.Boolean(string="Send Outputs", required=True,
                                default=True)
    glob = fields.Char(string="Filename Pattern", required=True, default='*')
    age_window = fields.Float(string="Age Window (in hours)", required=True,
                              default=24)
    doc_type_ids = fields.Many2many('edi.document.type',
                                    string="Document Types")


class EdiGateway(models.Model):
    """EDI Gateway

    An EDI Gateway is a remote file server used to send and/or receive
    EDI documents.
    """

    _name = 'edi.gateway'
    _description = "EDI Gateway"
    _inherit = ['edi.issues', 'mail.thread']

    # Basic fields
    name = fields.Char(string="Name", required=True, index=True)
    model_id = fields.Many2one('ir.model', string="Connection Model",
                               domain=[('is_edi_connection', '=', True)],
                               required=True, index=True)
    can_initiate = fields.Boolean(string="Initiate Connections",
                                  compute='_compute_can_initiate')
    server = fields.Char(string="Server Address")
    # Map the server address to the desired server
    outgoing_server_id = fields.Many2one(
        'ir.mail_server',
        string="Outgoing Server",
        compute='_compute_outgoing_server_id',
        readonly=True,
    )
    timeout = fields.Float(string="Timeout (in seconds)")
    safety = fields.Char(
        string="Safety Catch",
        help="""Configuration file option required for operation

        If present, this option must have a true value within the
        local configuration file in order for the gateway to initiate
        connections.
        """,
    )
    automatic = fields.Boolean(string="Process automatically", default=True)
    resend = fields.Boolean(string="Resend missing files", default=True)

    # Authentication
    username = fields.Char(string="Username")
    password = fields.Char(string="Password", invisible=True, copy=False)
    config_password = fields.Char(
        string="Password (Config)",
        help="""Configuration file option holding the password

        If present, the password is loaded from this configuration
        file option.  This allows the password to be hidden from
        database backups, XML-RPC calls, etc.
        """,
    )
    port = fields.Integer(string="Port")
    ssh_host_key = fields.Binary(string="SSH Host Key")
    ssh_host_key_filename = fields.Char(default=SSH_KNOWN_HOSTS)
    ssh_host_fingerprint = fields.Char(string="SSH Host Fingerprint",
                                       readonly=True, store=True,
                                       compute='_compute_ssh_host_fingerprint')

    # Issue tracking used for asynchronously reporting errors
    issue_ids = fields.One2many(inverse_name='edi_gateway_id')

    # Paths
    path_ids = fields.One2many('edi.gateway.path', 'gateway_id',
                               string="Paths")
    path_count = fields.Integer(string="Path Count",
                                compute='_compute_path_count')

    # Transfers
    transfer_ids = fields.One2many('edi.transfer', 'gateway_id',
                                   string="Transfers")
    transfer_count = fields.Integer(string="Transfer Count",
                                    compute='_compute_transfer_count')
    last_transfer_id = fields.Many2one('edi.transfer', string="Last Transfer",
                                       readonly=True, copy=False)

    # Documents
    doc_ids = fields.One2many('edi.document', 'gateway_id',
                              string="Documents", readonly=True)
    doc_count = fields.Integer(string="Document Count",
                               compute='_compute_doc_count')

    # Scheduled jobs
    cron_ids = fields.One2many('ir.cron', 'edi_gateway_id',
                               domain=[('state', '=', 'edi')],
                               string="Schedule")
    cron_count = fields.Integer(string="Schedule Count",
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

        # We use the read_group method to aggregate data from the edi.transfer model. 
        # We specify the search domain to filter transfers related to the current edi.gateway, 
        # group the results by gateway_id, and count the number of records for each group.
    
        transfers_data = self.env['edi.transfer'].read_group(
        [('gateway_id', 'in', self.ids)],
        ['gateway_id'], ['gateway_id'])
        transfer_count_dict = {data['gateway_id'][0]: data['gateway_id_count'] for data in transfers_data}
        for gw in self:
            gw.transfer_count = transfer_count_dict.get(gw.id, 0)

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
                line = base64.b64decode(gw.ssh_host_key).decode()
                entry = paramiko.hostkeys.HostKeyEntry.from_line(line)
                digest = entry.key.get_fingerprint()
                gw.ssh_host_fingerprint = ':'.join('%02x' % x for x in digest)
            else:
                gw.ssh_host_fingerprint = None

    @api.multi
    @api.depends('server', 'port')
    def _compute_outgoing_server_id(self):
        """Get the outgoing server from the smtp host name and port if supplied"""
        MailServer = self.env['ir.mail_server']
        for gw in self:
            if gw.server:
                domain = [('smtp_host', '=', gw.server)]
                if gw.port:
                    domain += [('smtp_port', '=', gw.port)]
                # Order the servers by priority as is default behaviour
                server = MailServer.search(domain, order='sequence asc',
                                           limit=1)
                if server:
                    gw.outgoing_server_id = server
                    _logger.info("Outgoing server for '%s' set to '%s' with "
                                 "address %s", gw.name, server.name, gw.server)
                else:
                    _logger.warning("Outgoing server '%s' not found - will "
                                    "use the server with the lowest priority",
                                    gw.server)
                    gw.outgoing_server_id = False
            else:
                # Server set to default
                _logger.info("No outgoing server set - will use the server "
                             "with the lowest priority")
                gw.outgoing_server_id = False

    @api.multi
    @api.constrains('password', 'config_password')
    def _check_passwords(self):
        for gw in self:
            if gw.password and gw.config_password:
                raise ValidationError(_("You cannot specify both a password "
                                        "and a password configuration option"))

    @api.multi
    def _get_password(self):
        """Get password (from database record or from configuration file)"""
        self.ensure_one()
        if self.password:
            return self.password
        if self.config_password:
            section, _sep, key = self.config_password.rpartition('.')
            password = config.get_misc(section or 'edi', key)
            if password is None:
                raise UserError(_("Missing configuration option '%s'") %
                                self.config_password)
            return password
        return None

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
            password = self._get_password()
            if password:
                kwargs['password'] = password
            if self.timeout:
                kwargs['timeout'] = self.timeout
                kwargs['banner_timeout'] = self.timeout
            if self.port:
                kwargs['port'] = self.port
            ssh.connect(self.server, **kwargs)
        except paramiko.SSHException as err:
            raise UserError(err) from err
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
        action['domain'] = [('state', '=', 'edi'),
                            ('edi_gateway_id', '=', self.id)]
        action['context'] = {
            'default_model_id': self.env['ir.model']._get_id('edi.gateway'),
            'default_state': 'edi',
            'default_edi_gateway_id': self.id,
            'default_numbercall': -1,
            'create': True
        }
        return action

    @api.multi
    def action_test(self):
        """Test connection"""
        self.ensure_one()
        Model = self.env[self.model_id.model]
        try:
            # pylint: disable=broad-except
            with Model.connect(self) as _conn:
                pass
        except Exception as err:
            self.raise_issue(_("Connection test failed: %s"), err)
            return False
        self.message_post(body=_("Connection tested successfully"))
        return True

    @api.multi
    def do_transfer(self, conn=None):
        """Receive input attachments, process documents, send outputs"""
        self.ensure_one()
        transfer = self.transfer_ids.create({
            'gateway_id': self.id,
            'allow_process': self._context.get('default_allow_process',
                                               self.automatic),
        })
        self.lock_for_transfer(transfer)
        Model = self.env[self.model_id.model]
        try:
            # pylint: disable=broad-except
            if not self.safety:
                raise UserError(_("Missing safety configuration option"))
            else:
                section, _sep, key = self.safety.rpartition('.')
                conf_file_safety = config.get_misc(section or 'edi', key)
                if conf_file_safety is None:
                    raise UserError(_("Missing configuration option '%s'") %
                                    self.safety)
                if not conf_file_safety:
                    raise UserError(_("Gateway disabled via configuration "
                                        "option '%s'") % self.safety)
                if self.safety and conf_file_safety:
                    if conn is not None:
                        with self.env.cr.savepoint(), self.env.clear_upon_failure():
                            transfer.do_transfer(conn)
                    else:
                        with Model.connect(self) as auto_conn,\
                                self.env.cr.savepoint(),\
                                self.env.clear_upon_failure():
                            transfer.do_transfer(auto_conn)
        except Exception as err:
            transfer.raise_issue(_("Transfer failed: %s"), err)
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

    @api.model
    def get_jail_path(self):
        """Jail Path
        Query the config file in order to get a path, to which the local filesystem access is restricted.
        First, query jail_path. If it does not exist, return None.
        *None must be handled at the point of use.*
        """
        jail_directory = config.get_misc('edi', 'jail_path', None)

        return jail_directory
