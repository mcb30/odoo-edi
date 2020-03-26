"""EDI raw import documents"""

import pathlib
import re
from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

OPTIONS = {
    'headers': True,
    'quoting': '"',
    'separator': ',',
}

TRIAL_COUNT = 10

MODEL_PATTERN = re.compile(r'.*?(?P<model>([a-z]+\.)+[a-z]+)$')


class TrialImport(Exception):
    """Exception raised in a trial import to trigger a savepoint rollback"""
    pass


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
    def automodel(self, fname):
        """Calculate model name from input filename"""
        m = MODEL_PATTERN.match(pathlib.Path(fname).stem)
        if m:
            return self.env.get(m.group('model'))

    @api.model
    def autotype(self, inputs):
        """Autodetect document type"""
        return [x for x in inputs if self.automodel(x.name) is not None]

    @api.model
    def importer(self, doc):
        """Construct importer"""
        Import = self.env['base_import.import']
        fname, data = doc.input()
        Model = self.automodel(fname)
        if Model is None:
            raise UserError(_("Unable to determine model from \"%s\"") % fname)
        importer = Import.create({
            'res_model': Model._name,
            'file': data,
            'file_name': fname,
        })
        return importer

    @api.model
    def import_data(self, doc, trial=None):
        """Import data"""
        IrModel = self.env['ir.model']

        # Construct importer
        importer = self.importer(doc)

        # Construct header list
        preview = importer.parse_preview(OPTIONS)
        if 'error' in preview:
            raise UserError(preview['error'])
        headers = preview['headers']

        # Parse import file
        raw, fields = importer._convert_import_data(headers, OPTIONS)
        assert fields == headers
        raw = importer._parse_import_data(raw, fields, OPTIONS)

        # Import raw data
        model = IrModel._get(importer.res_model)
        Model = self.env[model.model]
        try:
            with self.env.cr.savepoint():
                res = Model.load(fields, raw[:trial])
                msgs = res.get('messages')
                ids = res.get('ids')
                if trial:
                    ids = []
                    raise TrialImport
        except TrialImport:
            # Exception raised solely to trigger rollback to savepoint
            pass
        except KeyError as e:
            # Most likely an unrecognised column heading
            raise UserError(_("Unrecognised header \"%s\"") % e.args[0]) from e
        finally:
            importer.unlink()

        # Raise any errors from the import
        if msgs:
            raise UserError('\n'.join(x['message'] for x in msgs))

        # Return imported recordset
        return Model.browse(ids)

    @api.model
    def prepare(self, doc):
        """Prepare document"""
        super().prepare(doc)

        # Perform a trial import to validate input file
        self.import_data(doc, trial=TRIAL_COUNT)

    def _get_values(self, doc, recs):
        IrModel = self.env['ir.model']
        model = IrModel._get(recs._name)
        for index, rec in enumerate(recs, start=1):
            yield {
                'doc_id': doc.id,
                'name': '%05d' % index,
                'model_id': model.id,
                'res_id': rec.id,
            }
    @api.model
    def execute(self, doc):
        """Execute document"""
        super().execute(doc)
        EdiRawRecord = self.env['edi.raw.record']

        # Import data
        recs = self.import_data(doc)

        # Create EDI records for imported records
        EdiRawRecord.create(list(self._get_values(doc, recs)))
