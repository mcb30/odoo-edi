"""Base model enhancements"""

from odoo import models
from .. import tools

def add_if_not_exists(cls):
    """Patch class to add a new method"""
    def wrapper(func):
        # pylint: disable=missing-docstring
        if hasattr(cls, func.__name__):
            raise ImportError("%s.%s is already defined" %
                              (cls.__name__, func.__name__))
        setattr(cls, func.__name__, func)
        return func
    return wrapper

@add_if_not_exists(models.BaseModel)
def sliced(self, size=models.PREFETCH_MAX):
    """Return the recordset ``self`` split into slices of a specified size"""
    return tools.sliced(self, size=size,
                        concat=lambda s: self.browse(x.id for x in s))

@add_if_not_exists(models.BaseModel)
def batched(self, size=models.PREFETCH_MAX):
    """Return the recordset ``self`` split into batches of a specified size"""
    return tools.ranged(self.sliced(size=size))
