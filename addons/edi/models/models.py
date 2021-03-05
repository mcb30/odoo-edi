"""Base model enhancements"""

import itertools
from operator import itemgetter
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

@add_if_not_exists(models.BaseModel)
def groupby(self, key, sort=True):
    """Return the recordset ``self`` grouped by ``key``

    The recordset will automatically be sorted using ``key`` as the
    sorting key, unless ``sort`` is explicitly set to ``False``.

    ``key`` is permitted to produce a singleton recordset object, in
    which case the sort order will be well-defined but arbitrary.  If
    a non-arbitrary ordering is required, then use :meth:`~.sorted` to
    sort the recordset first, then pass to :meth:`~.groupby` with
    ``sort=False``.

    Any recordsets within a tuple in ``key`` will be replaced with a list of IDs from each
    recordset.
    """
    def tuple_contains_recordset(tup):
        """Returns True if the supplied tuple contains a recordset, otherwise False"""
        for item in tup:
            if isinstance(item, models.BaseModel):
                return True
        return False

    def get_ids_from_recordset_in_tuple(tup):
        """
        Replaces each Recordset found within the supplied tuple
        with a list of ids from that recordset
        """
        temp_key = []
        for item in tup:
            next_key = item
            if isinstance(next_key, models.BaseModel):
                next_key = next_key.ids
            elif isinstance(next_key, tuple) and tuple_contains_recordset(next_key):
                next_key = get_ids_from_recordset_in_tuple(next_key)
            temp_key.append(next_key)
        return tuple(temp_key)

    recs = self
    if isinstance(key, str):
        key = itemgetter(key)
    if sort:
        if recs:
            first_key = key(next(iter(recs)))
            if isinstance(first_key, models.BaseModel):
                recs = recs.sorted(key=lambda x: key(x).ids)
            elif isinstance(first_key, tuple) and tuple_contains_recordset(first_key):
                recs = recs.sorted(key=lambda x: get_ids_from_recordset_in_tuple(key(x)))
            else:
                recs = recs.sorted(key=key)
    return ((k, self.browse(x.id for x in v))
            for k, v in itertools.groupby(recs, key=key))

@add_if_not_exists(models.BaseModel)
def statistics(self, cache=False):
    """Gather profiling statistics for an operation"""
    return tools.EdiStatistics(self.env, cache=cache)

@add_if_not_exists(models.BaseModel)
def trace(self, filter=None, max=None):
    """Trace database queries"""
    return tools.EdiTracer(self.env.cr, filter=filter, max=max)
