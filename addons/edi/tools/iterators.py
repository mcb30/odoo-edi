"""Iterator helpers for EDI"""

from itertools import islice, repeat, takewhile

def sliced(iterable, size=1, concat=list):
    """Iterate over iterable in slices of a specified size"""
    iterator = iter(iterable)
    return takewhile(lambda x: x,
                     (concat(islice(iterator, size)) for x in repeat(None)))

def ranged(iterable, start=0):
    """Add range indicators to an iterable"""
    for batch in iterable:
        yield (range(start, start + len(batch)), batch)
        start += len(batch)

def batched(iterable, size=1):
    """Iterate over iterable in batches of a specified size"""
    return ranged(sliced(iterable, size=size))
