"""Iterator tests"""

from unittest import TestCase
from ..tools import batched


class TestBatched(TestCase):
    """Iterator tests"""

    def test01_basic(self):
        """Check basic functionality"""
        iterable = (x for x in (6, 7, 2, 5, 3, 4, 8, 2))
        self.assertEqual(list(batched(iterable, size=3)),
                         [(range(0, 3), [6, 7, 2]),
                          (range(3, 6), [5, 3, 4]),
                          (range(6, 8), [8, 2])])
