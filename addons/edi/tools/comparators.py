"""Comparator helpers for EDI"""

from collections import UserDict
from odoo import fields
from odoo.tools import float_compare


class Comparator(UserDict):
    """Mapping that produces a comparator function for each field of a model

    Each entry within the mapping is a comparator function that takes
    two arguments and returns a boolean indicating whether or not the
    arguments should be considered equal when considered as values for
    that field.

    Comparator functions are produced on demand and cached within the
    mapping.
    """

    def __init__(self, model):
        super().__init__()
        self.model = model

    def __missing__(self, key):
        field = self.model._fields[key]
        self.data[key] = self.comparator(field)
        return self.data[key]

    def comparator(self, field):
        """Construct comparator function"""
        if isinstance(field, fields.Many2one):
            return lambda x, y: (not x and not y) or (x.id == y)
        elif isinstance(field, fields.Float) and field.digits:
            (_precision, scale) = field.digits
            return lambda x, y: float_compare(x, y, precision_digits=scale) == 0
        return lambda x, y: (not x and not y) or (x == y)
