"""EDI raw import documents"""

import pathlib
from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

OPTIONS = {
    'headers': True,
    'quoting': '"',
    'separator': ',',
}


class EdiRawDocument(models.AbstractModel):
    """EDI raw import document

    This is a document model that uses the native Odoo raw CSV/Excel
    import format.  It can be used to allow raw imports to be handled
    via the EDI mechanism rather than the manual user interface.
    """

    _name = 'edi.raw.document'
    _inherit = 'edi.document.model'
    _description = "Raw Records"

    @api.model
    def autotype(self, inputs):
        """Autodetect document type"""
        return [x for x in inputs if
                pathlib.Path(x.datas_fname).stem in self.env]

    @api.model
    def importer(self, doc):
        """Construct importer"""
        Import = self.env['base_import.import']
        fname, data = doc.input()
        importer = Import.create({
            'res_model': pathlib.Path(fname).stem,
            'file': data,
            'file_name': fname,
        })
        return importer

    @api.model
    def headers(self, importer):
        """Construct header list"""

        # Generate preview
        preview = importer.parse_preview(OPTIONS)
        if 'error' in preview:
            raise UserError(preview['error'])

        # Construct and validate fields list
        headers = preview['headers']
        matches = preview['matches']
        fields = [matches.get(i) for i in range(len(headers))]
        unmatched = [
            header for header, field in zip(headers, fields) if not field
        ]
        if unmatched:
            raise UserError(_("No match for headers: %s") %
                            ', '.join(unmatched))
        return headers

    @api.model
    def prepare(self, doc):
        """Prepare document"""
        super().prepare(doc)

        # Check that input file can be parsed to produce a header list
        importer = self.importer(doc)
        self.headers(importer)

        # Delete importer
        importer.unlink()

    @api.model
    def execute(self, doc):
        """Execute document"""
        super().execute(doc)
        IrModel = self.env['ir.model']
        EdiRawRecord = self.env['edi.raw.record']

        # Parse import file
        importer = self.importer(doc)
        model = IrModel._get(importer.res_model)
        headers = self.headers(importer)
        raw, fields = importer._convert_import_data(headers, OPTIONS)
        assert fields == headers
        raw = importer._parse_import_data(raw, fields, OPTIONS)

        # Import raw data
        res = self.env[model.model].load(fields, raw)
        msgs = res.get('messages')
        res_ids = res.get('ids')
        if msgs:
            raise UserError('\n'.join(x['message'] for x in msgs))

        # Create EDI records for imported records
        for index, res_id in enumerate(res_ids, start=1):
            EdiRawRecord.create({
                'doc_id': doc.id,
                'name': '%05d' % index,
                'model_id': model.id,
                'res_id': res_id,
            })

        # Delete importer
        importer.unlink()
