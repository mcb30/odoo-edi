"""EDI raw import tests"""

from base64 import b64encode, b64decode
import re
from .common import EdiCase


class TestRaw(EdiCase):
    """EDI raw import tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc_type_raw = cls.env.ref("edi.raw_document_type")

    def create_raw(self, *filenames):
        """Create raw import document(s)"""
        EdiDocumentType = self.env["edi.document.type"]
        attachments = self.create_attachment(*filenames)
        docs = EdiDocumentType.autocreate(attachments)
        self.assertEqual(len(docs), len(filenames))
        self.assertEqual(docs.mapped("doc_type_id"), self.doc_type_raw)
        self.assertEqual(docs.mapped("input_ids"), attachments)
        return docs

    def test01_basic(self):
        """Basic execution"""
        User = self.env["res.users"]
        doc = self.create_raw("res.users.csv")
        self.assertTrue(doc.action_execute())
        recs = doc.raw_ids
        self.assertEqual(len(recs), 3)
        for rec in recs:
            self.assertEqual(rec.model_id.model, "res.users")
        users = User.browse([x.res_id for x in recs])
        users_by_login = {x.login: x for x in users}
        self.assertEqual(users_by_login["alice"].name, "Alice")
        self.assertEqual(users_by_login["bob"].name, "Bob")
        eve = users_by_login["eve"]
        self.assertEqual(eve, self.env.ref("__import__.user_eve"))
        self.assertEqual(
            eve.partner_id,
            self.env.ref("base.main_partner"),
        )
        self.assertEqual(doc.raw_count, 3)
        action = doc.action_view_raw()
        self.assertEqual(self.env[action["res_model"]].search(action["domain"]), users)

    def test02_unknown_format(self):
        """Unknown file format"""
        doc = self.create_raw("res.users.csv")
        doc.input_ids.name = "res.users.garbage"
        with self.assertRaisesIssue(doc):
            doc.action_prepare()

    def test03_unknown_field(self):
        """Unknown field in header row"""
        doc = self.create_raw("res.users.csv")
        attachment = doc.input_ids
        attachment.datas = b64encode(
            re.sub(b"login", b"not_the_login_field", b64decode(attachment.datas))
        )
        with self.assertRaisesIssue(doc):
            doc.action_prepare()

    def test04_invalid_xmlid(self):
        """Invalid value"""
        doc = self.create_raw("res.users.csv")
        attachment = doc.input_ids
        attachment.datas = b64encode(
            re.sub(
                b"base.main_partner",
                b"edi.nonexistent_xmlid",
                b64decode(attachment.datas),
            )
        )
        with self.assertRaisesIssue(doc):
            doc.action_execute()

    def test05_prefixed_filename(self):
        """Prefixed model name in filename"""
        doc = self.create_raw("res.users.csv")
        attachment = doc.input_ids
        attachment.name = "01-initial-res.users.csv"
        self.assertTrue(doc.action_execute())

    def test06_unknown_model(self):
        """Unrecognised model name in filename"""
        doc = self.create_raw("res.users.csv")
        attachment = doc.input_ids
        attachment.name = "01-initial-res.definitely.not.users.csv"
        with self.assertRaisesIssue(doc):
            doc.action_prepare()

    def test07_unrecognisable_filename(self):
        """Unrecognisable model name in filename"""
        doc = self.create_raw("res.users.csv")
        attachment = doc.input_ids
        attachment.name = "res.users-broken.csv"
        with self.assertRaisesIssue(doc):
            doc.action_prepare()
