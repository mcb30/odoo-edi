"""Iterator helpers for EDI"""

from itertools import islice, repeat, takewhile


def sliced(iterable, size=1, concat=list):
    """Iterate over iterable in slices of a specified size"""
    iterator = iter(iterable)
    return takewhile(lambda x: x, (concat(islice(iterator, size)) for x in repeat(None)))


def ranged(iterable, start=0):
    """Add range indicators to an iterable"""
    for batch in iterable:
        yield (range(start, start + len(batch)), batch)
        start += len(batch)


def batched(iterable, size=1):
    """Iterate over iterable in batches of a specified size"""
    return ranged(sliced(iterable, size=size))


class NoRecordValuesError(NotImplementedError):
    """Method for constructing EDI record value dictionaries is not used

    This exception can be raised by document models to indicate that
    the convenience method for constructing iterables of EDI record
    value dictionaries has not been implemented and should not be
    used.

    This allows a record model to identify situations in which the
    document model has chosen not to use the convenience methods for
    constructing iterables of EDI record value dictionaries, and
    therefore abandon the record preparation without any side effects
    (such as synchronizer records choosing to deactivate any unmatched
    records).
    """

    pass
