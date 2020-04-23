import json
import jsonschema
from pathlib import Path
from base64 import b64decode

from odoo.addons.edi_sale.tests.common import EdiSaleCase


class TestEdiSaleJSON(EdiSaleCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        EdiDocumentType = cls.env["edi.document.type"]
        IrModel = cls.env["ir.model"]
        Partner = cls.env["res.partner"]
        Title = cls.env["res.partner.title"]
        State = cls.env["res.country.state"]
        cls.rec_type_sale_forward = cls.env.ref("edi_sale_json.sale_forward_record_type")
        cls.rec_type_sale_line_forward = cls.env.ref("edi_sale_json.sale_line_forward_record_type")
        cls.doc_type_sale_forward_type = cls.env.ref("edi_sale_json.sale_forward_document_type")

        cls.dame_title = Title.create({"name": "Dame", "shortcut": "Dm"})
        cls.usa = cls.env["res.country"].create({"name": "USA"})
        cls.new_york = State.create({"name": "New York", "country_id": cls.usa.id, "code": "NY",})

        cls.alice = Partner.create(
            {
                "name": "Alice",
                "title": cls.dame_title.id,
                "street": "Central Park",
                "street2": "East 74th Street",
                "city": "New York",
                "zip": "10021",
                "state_id": cls.new_york.id,
            }
        )
        cls.sale = cls.create_sale(cls.alice)
        cls.create_sale_line(cls.sale, cls.apple, 5)
        cls.create_sale_line(cls.sale, cls.banana, 7)

        cls.sale_json_schema = json.load(
            Path(__file__).parent.joinpath("../data/sale_request_schema.json").resolve().open()
        )

    def _get_sale_forward_docs(self):
        return self.env["edi.document"].search(
            [("doc_type_id", "=", self.doc_type_sale_forward_type.id)]
        )

    def _get_json_from_output(self, output):
        return json.loads(b64decode(output.datas).decode("utf-8"))

    def test_confirm_creates_document(self):
        prev_docs = self._get_sale_forward_docs()
        self.sale.action_confirm()
        docs = self._get_sale_forward_docs() - prev_docs
        self.assertTrue(docs)

    def test_confirm_with_no_doc_types(self):
        prev_docs = self._get_sale_forward_docs()
        self.sale.edi_doc_type_ids = [(5, 0, 0)]  # Remove all doc types
        self.sale.action_confirm()
        docs = self._get_sale_forward_docs() - prev_docs
        self.assertFalse(docs)

    def test_check_json_output(self):
        prev_docs = self._get_sale_forward_docs()
        self.sale.action_confirm()
        docs = self._get_sale_forward_docs() - prev_docs
        self.assertEqual(len(docs.output_ids), 1)
        jsonschema.validate(self._get_json_from_output(docs.output_ids), self.sale_json_schema)
