"""EDI Mail connection tests"""

from unittest.mock import patch
from .common import EdiConnectionCase


class TestEdiConnectionMail(EdiConnectionCase):
    """EDI Mail connection tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        EdiGateway = cls.env['edi.gateway']
        EdiPath = cls.env['edi.gateway.path']
        IrModel = cls.env['ir.model']
        # Create EDI gateway
        cls.gateway = EdiGateway.create({
            'name': "Test mail gateway",
            'model_id': IrModel._get_id('edi.connection.mail'),
        })
        # Create EDI paths
        cls.path_alice = EdiPath.create({
            'name': "Alice",
            'gateway_id': cls.gateway.id,
            'path': "alice@example.com",
        })
        cls.path_bob = EdiPath.create({
            'name': "Bob",
            'gateway_id': cls.gateway.id,
            'path': "bob@example.com",
        })
        cls.path_eve = EdiPath.create({
            'name': "Eve",
            'gateway_id': cls.gateway.id,
            'path': "eve@example.com",
            'doc_type_ids': [(6, 0, cls.doc_type.ids)],
        })

    def setUp(self):
        super().setUp()
        Mail = self.env['mail.mail']
        # Mock mail.mail.send() to avoid actually sending e-mails
        patcher = patch.object(Mail.__class__, 'send', autospec=True)
        self.patched_send = patcher.start()
        self.addCleanup(patcher.stop)

    def test_empty(self):
        """Nothing is sent when there are no outputs"""
        self.gateway.do_transfer()

    def test_basic(self):
        """Send a single output attachment"""
        # Create output attachment and verify that it is sent
        self.attach_outputs(self.doc_today, self.att_save_world)
        self.gateway.do_transfer()
        self.assertEqual(self.patched_send.call_count, 1)
        mail = self.patched_send.call_args[0][0]
        self.assertEqual(mail.email_to, "eve@example.com")
        self.assertEqual(mail.attachment_ids, self.att_save_world)
        # Verify that attachment is not resent on a subsequent transfer
        self.gateway.do_transfer()
        self.patched_send.assert_called_once()
