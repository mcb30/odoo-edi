"""EDI product SAP IDocs"""

from itertools import groupby
from odoo import api, fields, models
from odoo.addons.edi.tools import sap_idoc_type, SapIDoc


Matmas01 = SapIDoc('edi_product', 'static', 'sapidoc', 'matmas01.txt')


class MaterialNumberGroupKey(object):
    """Key usable for grouping IDoc data records by material number"""

    def __init__(self):
        self.matnr = None

    def __call__(self, record):
        self.matnr = getattr(record, 'MATNR', self.matnr)
        return self.matnr


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include EDI product SAP IDoc records"""

    _inherit = 'edi.document'

    product_sap_ids = fields.One2many('edi.product.sap.record',
                                      'doc_id', string="Products")


class EdiProductSapRecord(models.Model):
    """EDI product SAP IDoc record"""

    _name = 'edi.product.sap.record'
    _inherit = 'edi.product.record'
    _description = "Product"

    name = fields.Char(help="MATNR in SAP IDoc")
    description = fields.Char(help="MAKTX in SAP IDoc")
    barcode = fields.Char(string="Barcode", readonly=True,
                          help="EAN11 in SAP IDoc")

    @api.model
    def target_values(self, record_vals):
        """Construct ``product.product`` field value dictionary"""
        product_vals = super().target_values(record_vals)
        product_vals.update({
            'barcode': record_vals['barcode'],
        })
        return product_vals


class EdiProductSapMatmas01(models.AbstractModel):
    """SAP MATMAS01 (Material Master) IDoc document model"""

    SAP_FIELD_MAP = {
        'MAKTX': 'description',
        'EAN11': 'barcode',
    }

    _name = 'edi.product.sap.document.matmas01'
    _inherit = 'edi.product.document'
    _description = "SAP MATMAS01 IDoc"

    @api.model
    def autotype(self, inputs):
        """Autodetect document type"""
        Attachment = self.env['ir.attachment']

        # Merge all IDoc attachments into a single EDI document, since
        # some standard SAP transactions (e.g. BD10 and BD21) will
        # send one IDoc per product by default.
        attachments = Attachment.union(
            *(x for x in inputs if sap_idoc_type(x) == ('MATMAS01', 'MATMAS'))
        )
        return [attachments] if attachments else []

    @api.model
    def product_record_values(self, data):
        """Construct EDI product record value dictionaries"""
        idoc = Matmas01(data)
        for matnr, irecs in groupby(idoc.data, key=MaterialNumberGroupKey()):
            record_vals = {
                'name': matnr,
                'description': matnr,
                'barcode': False
            }
            for irec in irecs:
                for attr, key in self.SAP_FIELD_MAP.items():
                    if hasattr(irec, attr):
                        value = getattr(irec, attr)
                        record_vals[key] = value if value is not None else False
            yield record_vals
