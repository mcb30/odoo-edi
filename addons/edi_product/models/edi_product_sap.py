"""EDI product SAP IDocs"""

from itertools import groupby
from odoo import api, fields, models
from odoo.addons.edi.tools import sap_idoc_type, SapIDoc


Matmas01 = SapIDoc('edi_product', 'static', 'sapidoc', 'matmas01.txt')


class MaterialNumberGroupKey(object):
    """A key usable for grouping IDoc data records by material number"""

    def __init__(self):
        self.matnr = None

    def __call__(self, record):
        self.matnr = getattr(record, 'MATNR', self.matnr)
        return self.matnr


class EdiDocument(models.Model):
    """Extend ``edi.document`` to include SAP products"""

    _inherit = 'edi.document'

    product_sap_ids = fields.One2many('edi.product.sap.record',
                                      'doc_id', string="Products")


class EdiProductSapRecord(models.Model):
    """An EDI product SAP IDoc record"""

    ROUNDING = 0.01

    _name = 'edi.product.sap.record'
    _inherit = 'edi.product.record'
    _description = "Product"

    name = fields.Char(help="MATNR in SAP IDoc")
    description = fields.Char(help="MAKTX in SAP IDoc")
    barcode = fields.Char(string="Barcode", readonly=True,
                          help="EAN11 in SAP IDoc")

    @api.multi
    def _product_values(self):
        """Construct ``product.product`` field value dictionary"""
        values = super()._product_values()
        if self.barcode is not False:
            values['barcode'] = self.barcode
        return values

    @api.model
    def _product_changed(self, product, values):
        """Check if existing ``product.product`` record should be changed"""
        return (super()._product_changed(product, values) or
                ('barcode' in values and product.barcode != values['barcode']))


class EdiProductSapMatmas01(models.AbstractModel):
    """SAP MATMAS01 (Material Master) IDoc"""

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
    def _record_values(self, data):
        """Construct EDI product record value dictionaries"""
        idoc = Matmas01(data)
        for matnr, recs in groupby(idoc.data, key=MaterialNumberGroupKey()):
            values = {
                key: getattr(rec, attr) or False
                for rec in recs
                for attr, key in self.SAP_FIELD_MAP.items()
                if hasattr(rec, attr)
            }
            values['name'] = matnr
            yield values
