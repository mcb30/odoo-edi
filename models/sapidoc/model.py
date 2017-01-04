"""IDoc Document Model

Abstract base classes, enumerations, and syntax trees for SAP IDocs.
"""

from collections import namedtuple
from enum import Enum


class Field(object):
    """IDoc field

    A single field within an IDoc record.
    """

    __slots__ = ['chars', 'len']

    def __init__(self, chars):
        self.chars = chars
        self.len = (self.chars.stop - self.chars.start + 1)

    def __get__(self, record, owner):
        """Get field value from containing record"""
        if record is None:
            return self
        value = record[self.chars].tobytes().strip()
        if value:
            return value

    def __set__(self, record, value):
        """Set field value in containing record"""
        record[self.chars] = value.ljust(self.len)


class CharacterField(Field):
    """IDoc character field"""

    __slots__ = []


class Record(object):
    """IDoc record

    A single control, data, or status record with an IDoc.
    """

    __slots__ = ['line']

    def __init__(self, line):
        self.line = line

    def __getitem__(self, key):
        """Get portion of raw record data"""
        return self.line[key]

    def __setitem__(self, key, value):
        """Set portion of raw record data"""
        self.line[key] = value

    def __repr__(self):
        """Generate printable representation"""
        cls = self.__class__
        fields = sorted(((k, getattr(self, k), getattr(cls, k).chars.start)
                         for k in dir(cls)
                         if (k != 'SDATA' and
                             isinstance(getattr(cls, k), Field) and
                             getattr(self, k) is not None)),
                         key=lambda (k, v, o): o)
        return ('%s(%s)' % (self.__class__.__name__,
                            ', '.join('%s=%r' % (k, v) for k, v, o in fields)))


class IDoc(object):
    """IDoc document"""

    __slots__ = ['control', 'data']

    def __init__(self, raw):
        lines = [memoryview(bytearray(x)) for x in raw.splitlines()]
        self.control = self.ControlRecord(lines.pop(0))
        self.data = [self.DataRecords[self.DataRecord(x).SEGNAM](x)
                     for x in lines]

    def __repr__(self):
        """Generate printable representation"""
        return ('%s(%r, %r)' %
                (self.__class__.__name__, self.control, self.data))

    def __str__(self):
        """Generate printable representation"""
        return ('%s\n%r\n%s' %
                (self.__class__.__name__, self.control,
                 '\n'.join(('%r' % x) for x in self.data)))


class Requirement(Enum):
    """IDoc mandatory/optional requirement level"""
    MANDATORY = True
    OPTIONAL = False


class Type(Enum):
    """IDoc field type"""
    CHARACTER = CharacterField


class Syntax(object):
    """IDoc abstract syntax tree"""

    def Node(name, fields):
        res = namedtuple(name, fields)
        res.__new__.__defaults__ = (None,) * len(res._fields)
        return res

    Field = Node('Field', ['name', 'text', 'type', 'length', 'field_pos',
                           'character_first', 'character_last'])

    ControlRecord = Node('ControlRecord', ['fields'])

    DataRecord = Node('DataRecord', ['fields'])

    StatusRecord = Node('StatusRecord', ['fields'])

    RecordSection = Node('RecordSection', ['control', 'data', 'status'])

    SegmentSection = Node('SegmentSection', ['idoc'])

    IDoc = Node('IDoc', ['name', 'segments'])

    Segment = Node('Segment', ['name', 'segmenttype', 'qualified', 'level',
                               'status', 'loopmin', 'loopmax', 'fields'])

    SegmentGroup = Node('SegmentGroup', ['number', 'level', 'status',
                                         'loopmin', 'loopmax', 'segments'])

    Document = Node('Document', ['records', 'segments'])
