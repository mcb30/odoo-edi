"""EDI partner records"""

from odoo import api, fields, models


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include EDI partner records"""

    _inherit = 'edi.document'

    partner_ids = fields.One2many('edi.partner.record', 'doc_id',
                                  string="Partners")
    partner_title_ids = fields.One2many('edi.partner.title.record', 'doc_id',
                                        string="Partner Titles")


class EdiPartnerRecord(models.Model):
    """EDI partner record

    This is the base model for EDI partner records.  Each row
    represents a partner that will be created or updated when the
    document is executed.

    The fields within each record represent the fields within the
    source document, which may not exactly correspond to fields of the
    ``res.partner`` model.  For example: the source document may
    define an address as a multiline text field, whereas the
    ``res.partner`` model has separate ``street``, ``street2``, and
    ``city`` fields.

    Derived models should implement :meth:`~.target_values`.
    """

    _name = 'edi.partner.record'
    _inherit = 'edi.record.sync.active'
    _description = "Partner"

    _edi_sync_target = 'partner_id'
    _edi_sync_via = 'ref'

    name = fields.Char(string="Internal Reference")
    partner_id = fields.Many2one('res.partner', string="Partner",
                                 required=False, readonly=True, index=True,
                                 auto_join=True)
    full_name = fields.Char(string="Name", required=True, readonly=True,
                            default="Anonymous")
    title_key = fields.Char(string="Title Key", required=False, readonly=True,
                            index=True, edi_relates='title_id.name')
    title_id = fields.Many2one('res.partner.title', string="Title",
                               required=False, readonly=True, index=True)

    @api.model
    def target_values(self, record_vals):
        """Construct ``res.partner`` field value dictionary"""
        partner_vals = super().target_values(record_vals)
        partner_vals.update({
            'name': record_vals['full_name'],
            'title': record_vals['title_id'],
        })
        return partner_vals

    @api.multi
    def missing_edi_relates_title_key(self, rel, key):
        """Handle missing partner title

        Create missing ``res.partner.title`` records automatically as
        needed, to avoid the requirement for EDI partner document
        models to use explicit EDI partner title records.
        """
        Record = self.browse()
        Target = Record[rel.target]
        return Target.create({rel.via: key})


class EdiPartnerTitleRecord(models.Model):
    """EDI partner title record

    This is the base model for EDI partner title records.  Each row
    represents a partner title that will be created or updated when
    the document is executed.

    Derived models should implement :meth:`~.target_values`.
    """

    _name = 'edi.partner.title.record'
    _inherit = 'edi.record.sync'
    _description = "Partner Title"

    _edi_sync_target = 'title_id'

    title_id = fields.Many2one('res.partner.title', string="Title",
                               required=False, readonly=True, index=True,
                               auto_join=True)
    shortcut = fields.Char(string="Abbreviation", readonly=True)

    @api.model
    def target_values(self, record_vals):
        """Construct ``res.partner.title`` field value dictionary"""
        title_vals = super().target_values(record_vals)
        title_vals.update({
            'shortcut': record_vals['shortcut'],
        })
        return title_vals
    
class EdiInactivePartnerRecord(models.Model):
    """EDI inactive prtner record"""

    _name = 'edi.inactive.partner.record'
    _inherit = 'edi.record.deactivator'
    _description = "???"

    target_id = fields.Many2one('res.partner', string="Partner")
