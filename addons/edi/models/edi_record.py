"""EDI records"""

import logging
from itertools import chain
from operator import attrgetter, itemgetter
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _
from odoo.osv import expression
from ..tools import NoRecordValuesError

_logger = logging.getLogger(__name__)


class EdiLookupRelationship(object):
    """An EDI lookup relationship

    A common pattern within EDI document processing is for EDI records
    to refer to other database records using a lookup key.  For
    example: a stock picking request from an external system may refer
    to products using the product code (as stored in
    ``product.product.default_code``).

    This will be represented within the EDI record as a pair of
    fields: one holding the lookup key value (e.g. the product
    ``default_code``) and the other holding the target record
    (e.g. the ``product_id``).

    The actual target record may be created during the execution of
    the EDI document; the target record field may therefore be empty
    when the EDI record is created.

    The ``edi_relates`` field attribute can be used to annotate a
    field as a lookup key, using a syntax similar to the standard
    ``related`` field attribute.

    The resulting list of EDI lookup relationships is available via
    the ``_edi_relates`` model attribute.
    """

    def __init__(self, key, target, via=None, domain=None):
        self.key = key
        self.target = target
        self.via = via if via else key
        self.domain = (domain if callable(domain) else
                       (lambda self: domain) if domain else
                       (lambda self: []))

    def __repr__(self):
        return '%s(%r, %r, %r)' % (self.__class__.__name__, self.key,
                                   self.target, self.via)


class EdiRecordType(models.Model):
    """EDI record type"""

    _name = 'edi.record.type'
    _description = "EDI Record Type"
    _order = 'sequence, id'

    name = fields.Char(string="Name", required=True, index=True)
    model_id = fields.Many2one('ir.model', string="Record Model",
                               required=True)
    doc_type_ids = fields.Many2many('edi.document.type',
                                    string="Document Types")
    sequence = fields.Integer(string="Sequence", help="Application Order")


class EdiRecord(models.AbstractModel):
    """EDI record

    This is the abstract base class for all EDI records.
    """

    BATCH_SIZE = 1000
    """Batch size for record processing

    This is typically used to obtain a sensible balance between the
    number of database queries and the number of records returned in
    each query.
    """

    BATCH_CREATE = property(attrgetter('BATCH_SIZE'))
    """Batch size for creating new records"""

    BATCH_UPDATE = property(attrgetter('BATCH_SIZE'))
    """Batch size for updating existing records"""

    _edi_relates = ()
    """EDI lookup relationships"""

    _edi_relates_required = True
    """EDI lookup relationships must succeed prior to execution

    Derived models may set this to ``False`` to indicate that EDI
    lookup relationships need not succeed prior to execution of the
    document.  This allows derived models to implement multi-stage
    execution with repeated calls to :meth:`~._add_edi_relates`,
    thereby allowing for lookup keys that refer to target records
    created within the same document.
    """

    _name = 'edi.record'
    _description = "EDI Record"
    _order = 'doc_id, id'

    name = fields.Char(string="Name", required=True, readonly=True,
                       index=True)
    doc_id = fields.Many2one('edi.document', string="EDI Document",
                             required=True, readonly=True, index=True,
                             ondelete='cascade')

    @api.model
    def _setup_complete(self):
        super()._setup_complete()
        # Construct EDI relationship list
        cls = type(self)
        cls._edi_relates = []
        for name, field in cls._fields.items():
            if hasattr(field, 'edi_relates'):
                (target, _sep, via) = field.edi_relates.partition('.')
                domain = getattr(field, 'edi_relates_domain', None)
                if domain is None:
                    domain = getattr(cls._fields[target], 'domain', None)
                rel = EdiLookupRelationship(name, target, via, domain)
                cls._edi_relates.append(rel)

    @api.multi
    def _add_edi_relates(self, required=True):
        """Add EDI lookup relationship target IDs to records

        Fill in any missing target IDs based on the EDI lookup
        relationships, where possible.
        """
        # pylint: disable=too-many-locals
        Record = self.browse()
        doc = self.mapped('doc_id')
        ready = self
        for rel in self._edi_relates:
            # pylint: disable=cell-var-from-loop

            # Find records missing a target, if any
            missing = self.filtered(lambda x: x[rel.key] and not x[rel.target])

            # Process records in batches to minimise database lookups
            keygetter = itemgetter(rel.key)
            for r, batch in missing.batched(self.BATCH_SIZE):
                _logger.info("%s recording %s.%s %d-%d of %d", doc.name,
                             self._name, rel.target, r[0], r[-1], len(missing))

                # Search for target records by key
                Target = Record[rel.target]
                targets = Target.search(expression.AND([
                    [(rel.via, 'in', list(set(keygetter(x) for x in batch)))],
                    rel.domain(Record),
                ]))
                targets_by_key = {k: v.ensure_one() for k, v in
                                  targets.groupby(rel.via)}

                # Update target fields
                for key, recs in batch.groupby(keygetter):
                    target = targets_by_key.get(key)
                    if required and not target:
                        target = recs.missing_edi_relates(rel, key)
                    if target:
                        recs.write({rel.target: target.id})
                    else:
                        ready -= recs
        return ready

    @api.multi
    def missing_edi_relates(self, rel, key):
        """Handle missing EDI lookup relationship targets

        Report (or create) missing EDI lookup relationship targets.
        Must either raise an exception or return a singleton record in
        the target model.
        """
        func = getattr(self, 'missing_edi_relates_%s' % rel.key, None)
        if func:
            return func(rel, key)
        Record = self.browse()
        Target = Record[rel.target]
        raise UserError(_("Cannot identify %s \"%s\"") %
                        (Target._description, key))

    @api.model
    def _add_edi_relates_vlist(self, vlist):
        """Add EDI lookup relationship target IDs to values dictionaries

        Fill in any missing target IDs based on the EDI lookup
        relationships, where possible.

        This is available as an operation on a list of raw values
        dictionaries to allow for the possibility of avoiding
        incurring the cost of creating full recordset objects for
        records that may be elided from the final document.
        """
        Record = self.browse()
        for rel in self._edi_relates:
            # pylint: disable=cell-var-from-loop

            # Find values with a defined key but missing a target, if any
            missing = [x for x in vlist
                       if x.get(rel.key) and rel.target not in x]
            if not missing:
                continue

            # Search for target records by key
            targets = self.browse()[rel.target].search(expression.AND([
                [(rel.via, 'in', list(set(x[rel.key] for x in missing)))],
                rel.domain(Record),
            ]))
            targets_by_key = {k: v.ensure_one() for k, v in
                              targets.groupby(rel.via)}

            # Add target values where known
            for vals in missing:
                target = targets_by_key.get(vals[rel.key])
                vals[rel.target] = target.id if target else models.NewId()

    @api.model
    def add_edi_defaults(self, target, vlist):
        """Add default values

        Add default values for the ``target`` model to each entry in
        the iterable ``vlist`` of value dictionaries that could be
        passed to :meth:`~odoo.models.Model.create` in order to create
        a record in the target model.

        Each value dictionary within the list must contain the same
        keys.  This allows the missing default values to be calculated
        only once, and so avoids incurring the typically high cost of
        adding missing default values for each newly created record.
        """
        iterator = iter(vlist)
        try:
            first = next(iterator)
        except StopIteration:
            return ()
        defaults = tuple(
            (k, v) for k, v in
            target._add_missing_default_values(first).items()
            if k not in first
        )
        return (dict(chain(defaults, vals.items()))
                for vals in chain((first,), iterator))

    @api.multi
    def precache(self):
        """Precache associated records

        Load any relevant associated records into the field value
        cache, to ensure that a bulk operation does not experience a
        cache miss that could potentially result in large numbers of
        single-record queries.
        """
        for rel in self._edi_relates:
            self.mapped('%s.%s' % (rel.target, rel.via))

    @api.model
    def prepare(self, doc, vlist):
        """Prepare records

        Accepts an EDI document ``doc`` and an iterable ``vlist``
        yielding value dictionaries that could be passed to
        :meth:`~odoo.models.Model.create` in order to create an EDI
        record.
        """

        # Initialise statistics
        count = 0
        _logger.info("%s preparing %s", doc.name, self._name)

        # Create records
        with self.statistics() as stats:
            try:
                for record_vals in vlist:
                    record_vals['doc_id'] = doc.id
                    self.create(record_vals)
                    count += 1
                self.recompute()
            except NoRecordValuesError:
                # Values dictionary iterable was not implemented (most
                # likely because the document model has chosen not to
                # use a convenience method)
                pass

        # Log statistics
        _logger.info("%s prepared %s in %.2fs, %d excess queries", doc.name,
                     self._name, stats.elapsed, (stats.count - count))

    @api.multi
    def execute(self):
        """Execute records"""

        # Fill in any EDI lookup relationship targets that did not
        # exist at the point that the EDI record was created
        # (i.e. when the EDI document was prepared).  This situation
        # can arise when a document has multiple EDI record types, and
        # the execution of earlier EDI records has created objects to
        # which this EDI record refers via a lookup relationship.
        #
        self._add_edi_relates(required=self._edi_relates_required)
