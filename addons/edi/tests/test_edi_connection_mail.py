"""EDI Mail connection tests"""

import base64
import pathlib
from unittest.mock import patch
from . import test_edi_gateway


class TestEdiConnectionMail(test_edi_gateway.EdiGatewayCase):
    """EDI Mail connection tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        IrModel = cls.env['ir.model']
        cls.gateway.write({
            'name': "Test mail gateway",
            'model_id': IrModel._get_id('edi.connection.mail'),
        })
        cls.gateway.path_ids.write({'allow_receive': False})
        cls.path_send.path = "eve@example.com"

    def setUp(self):
        super().setUp()
        Mail = self.env['mail.mail']
        # Mock mail.mail.send() to avoid actually sending e-mails
        patcher = patch.object(Mail.__class__, 'send', autospec=True)
        self.patched_send = patcher.start()
        self.addCleanup(patcher.stop)

    def assertSent(self, path_files):
        expected = frozenset(
            (path.path, frozenset((pathlib.PurePath(file).name,
                                   self.files.joinpath(file).read_bytes())
                                  for file in files))
            for path, files in path_files.items()
        )
        actual = frozenset(
            (mail.email_to, frozenset((attachment.datas_fname,
                                       base64.b64decode(attachment.datas))
                                      for attachment in mail.attachment_ids))
            for (mail, *args), kwargs in self.patched_send.call_args_list
        )
        self.assertEqual(actual, expected)
        self.patched_send.reset_mock()
