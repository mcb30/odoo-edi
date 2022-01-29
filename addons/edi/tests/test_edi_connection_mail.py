"""EDI Mail connection tests"""

import base64
import pathlib
from unittest.mock import patch
from . import test_edi_gateway


class TestEdiConnectionMail(test_edi_gateway.EdiGatewayConnectionCase):
    """EDI Mail connection tests"""

    can_initiate = True
    can_send = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        IrModel = cls.env["ir.model"]
        cls.gateway.write(
            {
                "name": "Test mail gateway",
                "model_id": IrModel._get_id("edi.connection.mail"),
            }
        )
        cls.path_send.path = "eve@example.com"

    def patch_paths(self, _path_files):
        """Patch EDI paths to include specified test files

        The ``mail.mail.send()`` method is mocked to avoid actually
        sending any e-mails.
        """
        Mail = self.env["mail.mail"]
        return patch.object(
            Mail.__class__,
            "send",
            autospec=True,
            side_effect=lambda self, **kwargs: self.write({"state": "sent"}),
        )

    def assertSent(self, ctx, path_files):
        """Assert that specified test files were sent

        The expected list of e-mails and attachments is compared
        against the actual list, obtained by inspecting the mocked
        ``mail.mail.send()`` method.
        """
        expected = frozenset(
            (
                path.path,
                frozenset(
                    (pathlib.PurePath(file).name, self.files.joinpath(file).read_bytes())
                    for file in files
                ),
            )
            for path, files in path_files.items()
        )
        actual = frozenset(
            (
                mail.email_to,
                frozenset(
                    (attachment.name, base64.b64decode(attachment.datas))
                    for attachment in mail.attachment_ids
                ),
            )
            for (mail, *args), kwargs in ctx.call_args_list
        )
        self.assertEqual(actual, expected)
