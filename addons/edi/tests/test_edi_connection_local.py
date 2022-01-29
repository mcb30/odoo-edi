"""EDI local filesystem connection tests"""

from contextlib import contextmanager
import pathlib
import os
import shutil
import tempfile
from unittest.mock import patch

from odoo import fields
from odoo.tools import config
from odoo.exceptions import UserError

from . import test_edi_gateway


class TestEdiConnectionLocal(test_edi_gateway.EdiGatewayFileSystemCase):
    """EDI local filesystem connection tests"""

    can_initiate = True
    can_receive = True
    can_send = True
    can_configure_resend = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        IrModel = cls.env["ir.model"]
        cls.gateway.write(
            {
                "name": "Test local filesystem gateway",
                "model_id": IrModel._get_id("edi.connection.local"),
            }
        )
        cls.path_receive.path = "receive"
        cls.path_send.path = "send"

    @contextmanager
    def patch_paths(self, path_files):
        """Patch EDI paths to include specified test files

        The ``edi.connection.local.connect()`` method is mocked to use
        a temporary local directory.
        """
        EdiConnectionLocal = self.env["edi.connection.local"]
        with super().patch_paths(path_files) as ctx:
            connect = lambda self, gateway: pathlib.Path(ctx.temppath)
            with patch.object(
                EdiConnectionLocal.__class__, "connect", autospec=True, side_effect=connect
            ):
                yield ctx

    def test01_no_config(self):
        with patch.object(config, "get_misc", autospec=True) as mock_get_misc:
            mock_get_misc.return_value = None

            self.assertEqual(self.gateway.get_jail_path(), None)
            mock_get_misc.assert_called_once_with("edi", "jail_path", None)
            mock_get_misc.reset_mock()

    @test_edi_gateway.skipUnlessCanReceive
    def test02_global_config(self):
        with tempfile.TemporaryDirectory() as tempdir, patch.object(
            config, "get_misc", autospec=True
        ) as mock_get_misc:
            mock_get_misc.return_value = tempdir

            self.assertEqual(self.gateway.get_jail_path(), tempdir)
            mock_get_misc.assert_called_once_with("edi", "jail_path", None)
            mock_get_misc.reset_mock()

            EdiDocument = self.env["edi.document"]
            EdiDocumentType = self.env["edi.document.type"]
            IrModel = self.env["ir.model"]

            doc_type = EdiDocumentType.create(
                {
                    "name": "Test EDI document",
                    "model_id": IrModel._get_id("edi.document.model"),
                }
            )
            self.path_receive.doc_type_ids = [doc_type.id]

            # Test reading from a valid location
            self.path_receive.path = tempdir

            test_src_path = os.path.join(self.files, "hello_world.txt")
            test_read_path = os.path.join(tempdir, "test_read")
            shutil.copyfile(test_src_path, test_read_path)

            transfer = self.gateway.do_transfer()

            self.assertEqual(len(transfer.input_ids), 1)
            self.assertEqual(len(transfer.output_ids), 0)
            self.assertAttachment(transfer.input_ids, "hello_world.txt", "test_read")

            # Test reading from an invalid path (fs root directory)
            self.path_receive.path = os.path.abspath(os.sep)

            with self.assertRaisesIssue(self.gateway, PermissionError):
                self.gateway.do_transfer()

            # Test writing to a valid location
            self.path_receive.path = tempdir  # Change it back
            self.path_send.path = tempdir

            today = fields.Datetime.now()
            doc = EdiDocument.create(
                {
                    "name": "ToDo list",
                    "doc_type_id": self.doc_type_unknown.id,
                    "state": "done",
                    "prepare_date": today,
                    "execute_date": today,
                }
            )
            attachment = self.create_output_attachment(doc, "hello_world.txt")
            transfer = self.gateway.do_transfer()
            self.assertEqual(len(transfer.input_ids), 0)
            self.assertEqual(len(transfer.output_ids), 1)
            self.assertIn(attachment, transfer.output_ids)

            # Test writing to an invalid location (fs root directory)
            self.path_send.path = os.path.abspath(os.sep)

            with self.assertRaisesIssue(self.gateway, PermissionError):
                self.gateway.do_transfer()

    @test_edi_gateway.skipUnlessCanSend
    def test03_path_in_file_name(self):
        """Local fs gateway used to accept filenames like ../../file, letting the user write
        to arbitrary locations.
        This checks if it throws an error in such a case."""
        EdiDocument = self.env["edi.document"]

        with tempfile.TemporaryDirectory() as tempdir, patch.object(
            config, "get_misc", autospec=True
        ) as mock_get_misc:
            mock_get_misc.return_value = tempdir

            today = fields.Datetime.now()
            doc = EdiDocument.create(
                {
                    "name": "ToDo list",
                    "doc_type_id": self.doc_type_unknown.id,
                    "state": "done",
                    "prepare_date": today,
                    "execute_date": today,
                }
            )

            self.path_receive.path = tempdir
            self.path_send.path = tempdir

            attachment = self.create_output_attachment(doc, "hello_world.txt")
            attachment.name = "../hack_it.txt"

            with self.assertRaisesIssue(self.gateway, PermissionError):
                self.gateway.do_transfer()
