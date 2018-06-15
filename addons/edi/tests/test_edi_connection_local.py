"""EDI Local connection tests"""

from .test_gateway import TestEDIGateway


class TestEDILocalGateway(TestEDIGateway):
    """EDI Local connection tests"""

    @classmethod
    def setUpClass(cls):
        super(TestEDILocalGateway, cls).setUpClass()

    def setUp(self):
        super(TestEDILocalGateway, self).setUp()

    def test01_gateway_action_test(self):

        gateway = self._create_local_gateway()
        self._create_local_path(gateway=gateway,
                                allow_send=False)
        self._test_action_test(gateway)

    def test02_gateway_do_transfer_no_path(self):

        gateway = self._create_local_gateway()
        self._test_do_transfer_no_path(gateway)

    def test03_gateway_do_transfer_receive(self):

        gateway = self._create_local_gateway()
        self._create_local_path(gateway=gateway,
                                allow_send=False)
        self._test_do_transfer_receive(gateway)

    def test04_gateway_do_transfer_receive_old_file_ignored(self):

        gateway = self._create_local_gateway()
        self._create_local_path(gateway=gateway,
                                touch_files=False,
                                folder='files/old',
                                age_window=0.01)
        self._test_do_transfer_receive_old_file_ignored(gateway)

    def test05_gateway_do_transfer_send(self):

        gateway = self._create_local_gateway()
        self._create_local_path(gateway=gateway,
                                folder='files/out',
                                glob='*.out',
                                allow_receive=False,
                                doc_type_ids=[(6, 0, [self.document_type_unknown.id])],
                                )
        self._test_do_transfer_send(gateway)

    def test06_gateway_action_transfer_no_path(self):

        gateway = self._create_local_gateway()
        self._test_action_transfer_no_path(gateway)
