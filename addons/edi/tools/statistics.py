"""Profiling statistics for EDI"""

from collections import defaultdict, namedtuple
import time

EdiMetrics = namedtuple("EdiMetrics", ("time", "count", "cache"))


class EdiCacheMetrics(set):
    """EDI cache usage metrics"""

    def __str__(self):
        return ", ".join(
            "%s:%d" % (recs._name, len(recs))
            for recs in sorted(list(self), key=lambda x: x._name)
            if recs
        )

    def __sub__(self, other):
        others = {x._name: x for x in other}
        return type(self)(x - others.get(x._name, x.browse()) for x in self)


class EdiStatistics(object):
    """EDI profiling statistics

    This is a lightweight profiling mechanism that captures the total
    elapsed time and query count.  It may be used as a standalone
    object or as a context manager.
    """

    def __init__(self, env, cache=False):
        self.env = env
        self.cache = cache
        self.start()
        self.stop()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    def metrics(self):
        """Get current profiling metrics"""
        ids = defaultdict(set)
        if self.cache:
            for field, records in self.env.cache._data.items():
                ids[field.model_name].update(k for k, v in records.items() if v)
        cache = EdiCacheMetrics(self.env[k].browse(v) for k, v in ids.items())
        return EdiMetrics(time=time.time(), count=self.env.cr.sql_log_count, cache=cache)

    def start(self):
        """Start profiling"""
        self.started = self.metrics()

    def stop(self):
        """Stop profiling"""
        self.stopped = self.metrics()

    @property
    def elapsed(self):
        """Elapsed time"""
        return self.stopped.time - self.started.time

    @property
    def count(self):
        """Query count"""
        return self.stopped.count - self.started.count

    @property
    def cached(self):
        """Newly cached records"""
        return self.stopped.cache - self.started.cache
