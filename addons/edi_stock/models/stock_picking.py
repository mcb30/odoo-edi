"""Trigger document"""

from odoo import api, fields, models


class StockPickingType(models.Model):
    """Extend ``stock.picking.type`` for automatic EDI document creation"""

    _inherit = 'stock.picking.type'

    edi_doc_type_ids = fields.Many2many(
        'edi.document.type',
        string="EDI document types",
    )
    edi_pick_report_autoemit = fields.Boolean(
        string="EDI autoemit",
        help="Create EDI pick report documents automatically",
        default=False,
    )
    x_enable_pick_cancellation_email_notifs = fields.Boolean(
        string="Enable Pick Cancellation Notifications",
        default=False,
        help="""
        When a pick using this picking type is cancelled,
        send an email out using the template defined in u_pick_cancellation_email_notif_template
        """,
    )
    x_pick_cancellation_email_notif_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Pick Cancellation Email Template",
        help="The email template to use for pick cancellation emails",
    )

    @api.multi
    def action_edi_pick_report(self):
        """Create EDI pick report"""
        EdiPickReportDocument = self.env['edi.pick.report.document']
        self.mapped('edi_doc_type_ids').filtered(
            lambda x: issubclass(type(self.env[x.model_id.model]),
                                 type(EdiPickReportDocument))
        ).autoemit()
        return True


class StockPicking(models.Model):
    """Extend ``stock.picking`` for automatic EDI document creation"""

    _inherit = 'stock.picking'

    @api.multi
    def action_done(self):
        """Extend action done to trigger creation of EDI documents"""
        res = super().action_done()
        self.mapped('picking_type_id').filtered(
            lambda x: x.edi_pick_report_autoemit
        ).action_edi_pick_report()
        return res
