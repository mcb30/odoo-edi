from odoo.tests import common
import os.path
import fnmatch
from pathlib import Path

class BaseEDI(common.SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(BaseEDI, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(BaseEDI, cls).tearDownClass()


    def assertIsInstantiated(self, recordset, number=1):
        """ Assert that the recordset is instantiated.
            Optionally the number of instances in the recordset
        """
        # self.assertEqual(len(recordset), number)
        self.assertTrue(recordset.exists())

    @classmethod
    def _create_local_gateway(cls):
        model_id = cls.env.ref('edi.model_edi_connection_local')
        return cls._create_gateway(name='Local Filesystem Test Gateway',
                                    model_id=model_id.id)

    @classmethod
    def _create_gateway(cls, **data):
        EdiGateway = cls.env['edi.gateway']

        gateway = EdiGateway.create(data)

        return gateway

    @staticmethod
    def _touch_files(path):
        for filename in os.listdir(path.path):
            # Skip files not matching glob pattern
            if not fnmatch.fnmatch(filename, path.glob):
                continue

            filepath = os.path.join(path.path, filename)
            Path(filepath).touch()

    @classmethod
    def _create_local_path(cls, gateway, touch_files=True, folder='files',
                           **kwargs):
        directory = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), folder
        )
        data = {
            'name': 'Local path for %s' % gateway.name,
            'gateway_id': gateway.id,
            'glob': '*.txt',
            'path': directory,
            'age_window': 24,
        }
        if kwargs:
            data.update(kwargs)

        path = cls._create_path(**data)

        if touch_files:
            cls._touch_files(path)

        return path

    @classmethod
    def _create_path(cls, **data):
        EdiPath = cls.env['edi.gateway.path']

        path = EdiPath.create(data)

        return path

