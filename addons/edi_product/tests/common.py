"""EDI product tests"""

import pathlib
from odoo.modules.module import get_resource_path
from odoo.addons.edi.tests.common import EdiCase


class EdiProductCase(EdiCase):
    """Base test case for EDI product models"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.files = pathlib.Path(
            get_resource_path('edi_product', 'tests', 'files')
        )
