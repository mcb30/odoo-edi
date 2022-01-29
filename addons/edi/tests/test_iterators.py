"""Iterator tests"""

from unittest import TestCase
from ..tools import batched


class TestBatched(TestCase):
    """Iterator tests"""

    def test01_basic(self):
        """Check basic functionality"""
        iterable = (x for x in (6, 7, 2, 5, 3, 4, 8, 2))
        self.assertEqual(
            list(batched(iterable, size=3)),
            [(range(0, 3), [6, 7, 2]), (range(3, 6), [5, 3, 4]), (range(6, 8), [8, 2])],
        )

    def test02_empty(self):
        """Check empty list"""
        iterable = (x for x in ())
        self.assertEqual(list(batched(iterable, size=3)), [])

    def test03_oversized(self):
        """Check oversized list length"""
        iterable = (x for x in (1, 5, 2, 8))
        self.assertEqual(list(batched(iterable, size=10)), [(range(0, 4), [1, 5, 2, 8])])

    def test04_exactlist(self):
        """Check only one range of exact length"""
        iterable = (x for x in (14, 11, 3, 7, 9, 4, 1))
        self.assertEqual(list(batched(iterable, size=7)), [(range(0, 7), [14, 11, 3, 7, 9, 4, 1])])

    def test05_onevalue(self):
        """Check one value"""
        iterable = (x for x in (1,))
        self.assertEqual(list(batched(iterable, size=1)), [(range(0, 1), [1])])

    def test06_mixedlist(self):
        """Check mixed list"""
        iterable = (x for x in (8, 10, "Grace", 5, 4, 6, 10, "Steve", 12))
        self.assertEqual(
            list(batched(iterable, size=5)),
            [(range(0, 5), [8, 10, "Grace", 5, 4]), (range(5, 9), [6, 10, "Steve", 12])],
        )
