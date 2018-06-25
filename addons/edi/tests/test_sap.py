"""SAP IDoc tests"""

import base64
from ..tools import sap_idoc_type, SapIDoc
from .common import EdiCase


class TestSapIDoc(EdiCase):
    """SAP IDoc tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.chocolate = cls.create_attachment('chocolate.txt')
        cls.hello = cls.create_attachment('hello_world.txt')

    def test01_idoc_type(self):
        """Test detection of IDoc type"""
        self.assertEqual(sap_idoc_type(self.chocolate), ('MATMAS01', 'MATMAS'))
        self.assertIsNone(sap_idoc_type(self.hello))

    def test02_parser(self):
        """Test IDoc parsing"""
        Matmas01 = SapIDoc('edi', 'tests', 'files', 'matmas01.txt')
        idoc = Matmas01(base64.b64decode(self.chocolate.datas))
        self.assertEqual(idoc.control.DOCNUM, "0000000000198012")
        self.assertEqual(len(idoc.data), 4)
        self.assertEqual(idoc.data[0].SEGNAM, "E2MARAM009")
        self.assertEqual(idoc.data[0].NTGEW, "275.000")
        self.assertEqual(idoc.data[1].MAKTX, "Chocolate chunk cookie mix")
        self.assertEqual(idoc.data[2].GEWEI, "GRM")
        self.assertEqual(idoc.data[3].EAN11, "5010251522676")
