"""SAP IDoc tests"""

import base64
from collections import namedtuple
from ..tools import sap_idoc_type, SapIDoc
from ..tools.sapidoc.model import CharacterField
from .common import EdiCase


class TestSapIDoc(EdiCase):
    """SAP IDoc tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.chocolate = cls.create_attachment("chocolate.txt")
        cls.hello = cls.create_attachment("hello_world.txt")

    def test_idoc_type(self):
        """Test detection of IDoc type"""
        self.assertEqual(sap_idoc_type(self.chocolate), ("MATMAS01", "MATMAS"))
        self.assertIsNone(sap_idoc_type(self.hello))

    def test_parser(self):
        """Test IDoc parsing"""
        # pylint: disable=eval-used
        Matmas01 = SapIDoc("edi", "tests", "files", "matmas01.txt")
        idoc = Matmas01(base64.b64decode(self.chocolate.datas))
        self.assertIsInstance(idoc.data[0].__class__.SEGNAM, CharacterField)
        self.assertEqual(idoc.control.DOCNUM, "0000000000198012")
        self.assertEqual(len(idoc.data), 4)
        self.assertEqual(idoc.data[0].SEGNAM, "E2MARAM009")
        self.assertEqual(idoc.data[0].NTGEW, "275.000")
        self.assertEqual(idoc.data[1].MAKTX, "Chocolate chunk cookie mix")
        self.assertEqual(idoc.data[2].GEWEI, "GRM")
        self.assertEqual(idoc.data[3].EAN11, "5010251522676")
        self.assertEqual(idoc.data[3].EANTP, "HE")  # next field in line
        idoc.data[3].EAN11 = "5055365625417"
        self.assertEqual(idoc.data[3].EAN11, "5055365625417")
        self.assertEqual(idoc.data[3].EANTP, "HE")  # next field in line
        self.assertIn("EAN11='5055365625417'", repr(idoc.data[3]))
        self.assertIn("EAN11='5055365625417'", repr(idoc))
        self.assertIn("DOCNUM='0000000000198012'", repr(idoc))
        self.assertIn("DOCNUM='0000000000198012'", str(idoc))
        rep = eval(
            repr(idoc.data[0]),
            {
                "MATMAS01": namedtuple("MATMAS01", ["E2MARAM009"])(dict),
            },
        )
        self.assertEqual(rep["ERSDA"], "20180605")
