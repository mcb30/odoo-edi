from . import common
import os.path

from odoo.exceptions import UserError, ValidationError


class TestEDIGateway(common.BaseEDI):

    @classmethod
    def setUpClass(cls):
        super(TestEDIGateway, cls).setUpClass()

    def setUp(self):
        super(TestEDIGateway, self).setUp()

    def _test_action_test(self):
        """ Test action test to check connection is fine """

        old_messages = self.gateway.message_ids

        self.gateway.action_test()
        new_message = self.gateway.message_ids - old_messages
        self.assertEqual(len(new_message), 1)
        # self.assertIsInstantiated(new_message)
        self.assertIn("Connection tested successfully", new_message.body)

    def _test_do_transfer_no_path(self):
        """ Test do transfer with no path, which means a transfer
            is created but nothing received
        """

        old_transfers = self.gateway.transfer_ids

        transfer = self.gateway.do_transfer()
        new_transfer = self.gateway.transfer_ids - old_transfers
        self.assertEqual(new_transfer, transfer)
        self.assertEqual(len(transfer.issue_ids), 0)

    def _test_do_transfer_receive(self):
        """ Test do transfer with input path, which means a transfer
            is created and a file is received
        """

        # first transfer receives dummy file
        old_transfers = self.gateway.transfer_ids
        transfer = self.gateway.do_transfer()
        new_transfer = self.gateway.transfer_ids - old_transfers
        self.assertEqual(new_transfer, transfer)
        issue = transfer.issue_ids
        self.assertEqual(len(issue), 1)
        self.assertIn('Unknown document type', issue.name)
        self.assertEqual(len(transfer.input_ids), 1)

        # second transfer ignores dummy file
        old_transfers = self.gateway.transfer_ids
        transfer = self.gateway.do_transfer()
        new_transfer = self.gateway.transfer_ids - old_transfers
        self.assertEqual(new_transfer, transfer)
        self.assertEqual(len(transfer.input_ids), 0)

    def _test_do_transfer_receive_old_file_ignored(self):
        """ Test do transfer with input path to an old file,
            which means a transfer is created but nothing received
        """

        old_transfers = self.gateway.transfer_ids
        transfer = self.gateway.do_transfer()
        new_transfer = self.gateway.transfer_ids - old_transfers
        self.assertEqual(new_transfer, transfer)
        self.assertEqual(len(transfer.input_ids), 0)

    def _test_do_transfer_send(self):
        """ Test do transfer with output path """

        # create document in state completed
        self.assertTrue(True)


class TestEDILocalGateway(TestEDIGateway):

    @classmethod
    def setUpClass(cls):
        super(TestEDILocalGateway, cls).setUpClass()
        cls.empty_gateway = cls._create_local_gateway()
        cls.gateway = cls._create_local_gateway()
        cls._create_local_path(gateway=cls.gateway,
                               allow_send=False)
        cls._create_local_path(gateway=cls.gateway,
                               folder='files/out',
                               allow_receive=False)
        cls.gateway_old_files = cls._create_local_gateway()
        cls._create_local_path(gateway=cls.gateway_old_files,
                               touch_files=False,
                               folder='files/old',
                               age_window=0.01)

    def setUp(self):
        super(TestEDILocalGateway, self).setUp()

    def test01_gateway_action_test(self):
        self.gateway = self._create_local_gateway()
        self._create_local_path(gateway=self.gateway,
                                allow_send=False)
        self._test_action_test()

    def test02_gateway_do_transfer_no_path(self):
        """ Create local gateway """

        self.gateway = self._create_local_gateway()

        self._test_do_transfer_no_path()

    def test03_gateway_do_transfer_receive(self):
        """ Create local gateway """

        self.gateway = self._create_local_gateway()
        self._create_local_path(gateway=self.gateway,
                                allow_send=False)
        self._test_do_transfer_receive()

    def test04_gateway_do_transfer_receive_old_file_ignored(self):

        self.gateway = self._create_local_gateway()
        self._create_local_path(gateway=self.gateway,
                                touch_files=False,
                                folder='files/old',
                                age_window=0.01)


        self._test_do_transfer_receive_old_file_ignored()

    def test05_gateway_do_transfer_send(self):

        self.gateway = self._create_local_gateway()
        self._create_local_path(gateway=self.gateway,
                                folder='files/out',
                                allow_receive=False)

        self._test_do_transfer_send()
