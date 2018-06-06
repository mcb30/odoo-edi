"""Iterator helpers for EDI"""

from itertools import count, zip_longest

def batched(iterable, size=1):
    """Iterate over iterable in batches of a specified size"""
    class Filler(object):
        """Unambiguously identifiable fill value for use with ``zip_longest``"""
        pass
    iterator = iter(iterable)
    batches = (list(x for x in batch if x is not Filler)
               for batch in zip_longest(*[iterator] * size, fillvalue=Filler))
    for start, batch in zip(count(step=size), batches):
        yield (range(start, start + len(batch)), batch)
