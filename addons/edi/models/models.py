"""Base model enhancements"""

import logging
import itertools
from operator import itemgetter
from odoo import models
from .. import tools

_logger = logging.getLogger(__name__)


def add_if_not_exists(cls):
    """Patch class to add a new method"""

    def wrapper(func):
        # pylint: disable=missing-docstring
        if hasattr(cls, func.__name__):
            _logger.debug("%s.%s is already defined" % (cls.__name__, func.__name__))
        else:
            setattr(cls, func.__name__, func)
        return func

    return wrapper


def add_even_if_exists(cls):
    """Patch class to override an existing method"""

    def wrapper(func):
        # pylint: disable=missing-docstring
        if hasattr(cls, func.__name__):
            _logger.debug("%s.%s is being overridden" % (cls.__name__, func.__name__))
        setattr(cls, func.__name__, func)
        return func

    return wrapper


@add_if_not_exists(models.BaseModel)
def sliced(self, size=models.PREFETCH_MAX):
    """Return the recordset ``self`` split into slices of a specified size"""
    return tools.sliced(self, size=size, concat=lambda s: self.browse(x.id for x in s))


@add_if_not_exists(models.BaseModel)
def batched(self, size=models.PREFETCH_MAX):
    """Return the recordset ``self`` split into batches of a specified size"""
    return tools.ranged(self.sliced(size=size))


def getter(key):
    func = None
    for x in key.split("."):
        if func is None:
            func = itemgetter(x)
        else:
            func = lambda y, _func=func: itemgetter(x)(_func(y))
    return func


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
    """

    recs = self
    if isinstance(key, str):
        key = getter(key)
    if sort:
        if recs and isinstance(key(next(iter(recs))), models.BaseModel):
            recs = recs.sorted(key=lambda x: key(x).ids)
        else:
            recs = recs.sorted(key=key)
    return ((k, self.browse(x.id for x in v)) for k, v in itertools.groupby(recs, key=key))


@add_if_not_exists(models.BaseModel)
def statistics(self, cache=False):
    """Gather profiling statistics for an operation"""
    return tools.EdiStatistics(self.env, cache=cache)


@add_if_not_exists(models.BaseModel)
def trace(self, filter=None, max=None):
    """Trace database queries"""
    return tools.EdiTracer(self.env.cr, filter=filter, max=max)


@add_even_if_exists(models.BaseModel)
def _valid_field_parameter(self, field, name):
    """Override function from odoo/odoo/models.py to include
    edi_relates as a valid field parameter on the basemodel.
    This prevents a warning on each model edi_relates is implemented on,
    without breaking inheritance to this method on other models"""
    allowed_params = ["related_sudo"]  # From odoo/odoo/models.py
    # Only allow the parameter if our model stems from edi.record or _is_ edi.record
    # When uninstalling models we can get a keyerror so check it exists first
    EdiRecord = self.env.get("edi.record", None)

    if EdiRecord is not None and issubclass(self.__class__, EdiRecord.__class__):
        allowed_params.append("edi_relates")
    return name in allowed_params
