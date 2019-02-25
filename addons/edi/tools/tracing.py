"""Query tracing"""

import time
from itertools import takewhile
import logging
import re
import traceback
from odoo import models
from odoo.sql_db import Cursor

try:
    import ipdb
    DEBUGGER = ipdb
except ImportError:
    try:
        import pdb
        DEBUGGER = pdb
    except ImportError:
        DEBUGGER = None


_logger = logging.getLogger(__name__)


# Patch base Cursor class to provide "tracing" attribute
Cursor.tracing = False


class EdiTracer(object):
    """Query tracer

    A query tracer can be used to temporarily wrap the ``execute``
    method on a database cursor in order to log selected queries.  The
    logged queries will be shown along with the query parameters and
    an incremental traceback.

    The incremental traceback will omit any stack frames that are
    identical between the point of creating the query tracer and the
    point of executing the query.  This typically produces a traceback
    showing only the portions of interest.

    The optional ``filter`` argument may be used to limit the queries
    that are logged.  ``filter`` may be a case-insensitive regular
    expression string used to match against the query string, an
    instance of ``BaseModel``, or a callable taking the query string
    as a single argument.  Any other value for ``filter`` will be
    treated as a truth value.

    Example useful filter expressions:

        # Trace all INSERTs
        filter='INSERT'

        # Trace all UPDATEs
        filter='UPDATE'

        # Trace all queries touching a field named "scheduled_date"
        filter='scheduled_date'

        # Trace all queries touching the res.partner model table
        filter='res_partner'

        # Trace all queries touching res.partner (alternative approach)
        filter=self.env['res.partner']

        # Trace all INSERT queries if there are more than 100 records
        filter=(len(self) > 100 and 'INSERT')

    The optional ``max`` parameter may be used to limit the total
    number of queries that are logged.

    The optional ``time_queries`` parameter is used to specify if the duration
    of queries should be logged.

    The optional ``breakpoint`` parameter takes a function which
    accepts the keyword arguemnts query, params (query parameters) and
    duration. If the function returns true then set_trace will be called on
    the debugger, assuming a debugger (ipdb or pdb) can be imported

    The query tracer may either be used as a context manager, in which
    case query tracing will be stopped automatically.

    The ``stop`` method allows tracing to be stopped for a query
    tracer that is not used as a context manager.

    """

    def __init__(self, cr, filter=None, max=None, time_queries=False,
                 breakpoint=None):
        self.cr = cr
        self.execute = cr.execute
        if filter is None:
            self.filter = True
        elif isinstance(filter, models.BaseModel):
            self.filter = re.compile('"%s"' % filter._table).search
        elif isinstance(filter, str):
            self.filter = re.compile(filter, re.I).search
        else:
            self.filter = filter
        self.max = max
        self.count = 0
        self.time_queries = time_queries
        self.breakpoint = breakpoint
        self.tb = traceback.extract_stack()
        self.start()

    def trace(self, query, params=None, log_exceptions=None):
        """Trace query"""

        # Log any queries matching the filter
        if not callable(self.filter) or self.filter(query):

            # Count logged queries, if applicable
            if self.max is not None:
                self.count += 1
                if self.count >= self.max:
                    self.stop()

            # Skip all but the innermost common stack frames
            full_tb = traceback.extract_stack()[:-1]
            init_tb = iter(self.tb)
            common = takewhile(lambda x: x == next(init_tb, None), full_tb)
            skip = max((len(list(common)) - 1), 0)
            tb = full_tb[skip:]

        if self.time_queries:
            start = time.time()
        else:
            # Log query, parameters, and incremental traceback
            _logger.info("query: %s : %s\n%s", query, params,
                         ''.join(traceback.format_list(tb)))

        res = self.execute(query, params=params, log_exceptions=log_exceptions)

        if self.time_queries:
            duration = time.time() - start
            # Log query, parameters, duration and incremental traceback
            _logger.info(
                "query: %s : %s\nduration: %s\n%s",
                query, params, duration, ''.join(traceback.format_list(tb))
            )

        if DEBUGGER is not None and callable(self.breakpoint):
            if self.breakpoint(
                duration=duration,
                query=query,
                params=params,
            ):
                DEBUGGER.set_trace()

        return res

    def start(self):
        """Start tracing queries"""
        self.count = 0
        if self.filter:
            self.cr.execute = self.trace
            self.cr.tracing = True

    def stop(self):
        """Stop tracing queries"""
        self.cr.execute = self.execute
        self.cr.tracing = False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.stop()
