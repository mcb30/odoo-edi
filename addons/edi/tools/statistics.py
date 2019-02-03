"""Profiling statistics for EDI"""

from collections import namedtuple
import time

EdiMetrics = namedtuple('EdiMetrics', ('time', 'count'))


class EdiStatistics(object):
    """EDI profiling statistics

    This is a lightweight profiling mechanism that captures the total
    elapsed time and query count.  It may be used as a standalone
    object or as a context manager.
    """

    def __init__(self, env):
        self.env = env
        self.start()
        self.stop()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    def metrics(self):
        """Get current profiling metrics"""
        return EdiMetrics(time=time.time(), count=self.env.cr.sql_log_count)

    def start(self):
        """Start profiling"""
        self.started = self.metrics()

    def stop(self):
        """Stop profiling"""
        self.stopped = self.metrics()

    @property
    def elapsed(self):
        """Elapsed time"""
        return (self.stopped.time - self.started.time)

    @property
    def count(self):
        """Query count"""
        return (self.stopped.count - self.started.count)
