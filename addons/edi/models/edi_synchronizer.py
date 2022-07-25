"""EDI synchronizer documents"""

import logging
from odoo import api, fields, models
from odoo.osv import expression

from odoo.odoo.exceptions import ValidationError
from ..tools import batched, Comparator

_logger = logging.getLogger(__name__)

PRECACHE_WARNING_THRESHOLD = 50
"""Minimum threshold for precache warning message

A warning message will be displayed for EDI synchronizer record models
that do not precache records appropriately.  The warning is displayed
if the number of queries is greater than the number of records (prior
to elision), since this would indicate that a fresh query had to be
performed for each record.

For very small numbers of records, the fixed number of queries
required to perform precaching may be greater than the actual number
of records.  The warning is therefore disabled below this threshold
value.
"""


class EdiSyncDocumentModel(models.AbstractModel):
    """EDI synchronizer document model

    This is the base model for EDI documents that synchronize Odoo
    records from an external data source.  For example, an EDI product
    document may synchronize records in ``product.product`` to match
    definitions provided in a supplier's material master file.

    Each row represents a collection of EDI records that, in turn,
    each represent an Odoo record that will be created or updated when
    the document is executed.

    Synchronized record definitions typically change infrequently.  To
    minimise unnecessary duplication, any EDI records that would not
    result in a new or modified Odoo record will be automatically
    elided from the document.
    """

    _name = "edi.document.sync"
    _inherit = "edi.document.model"
    _description = "EDI Synchronizer Document"


class EdiSyncRecord(models.AbstractModel):
    """EDI synchronizer record

    This is the base model for EDI records that synchronize Odoo
    records from an external data source.  Each row represents an Odoo
    record that will be created or updated when the document is
    executed.

    The fields within each record represent the fields within the
    source document, which may not exactly correspond to fields of the
    corresponding Odoo model.  For example: the source document may
    define a product weight as an integer number of grams, whereas the
    ``product.product.weight`` field is defined as a floating point
    number of kilograms.
    """

    _edi_relates_required = False

    _edi_sync_target = None
    """EDI synchronizer target field

    This is the name of the EDI record relational field mapping to the
    target Odoo record.
    """

    _edi_sync_via = "name"
    """EDI synchronizer target model lookup key field

    This is the name of the field within the target Odoo model used to
    identify the corresponding target record.  Defaults to ``name``.
    """

    _edi_sync_domain = None
    """EDI synchronizer target domain

    This is an additional search domain applied to the target Odoo
    model when identifying the corresponding target record.
    """

    _edi_sync_dedupe = True
    """Automatically elide duplicate record values

    Elide any duplicate EDI records (in addition to eliding any EDI
    records that would not result in a new or modified Odoo record).

    This is enabled by default.  Derived models that do not require a
    deduplication check (e.g. because the corresponding document model
    guarantees never to attempt to create duplicate EDI records) may
    set this to ``False`` to gain a slight improvement in performance.
    """

    _name = "edi.record.sync"
    _inherit = "edi.record"
    _description = "EDI Synchronizer Record"

    _sql_constraints = [
        (
            "doc_name_uniq",
            "unique (doc_id, name)",
            "Each synchronizer key may appear at most once per document",
        )
    ]

    @api.model
    def _setup_complete(self):
        """Complete the model setup"""
        super()._setup_complete()
        cls = type(self)
        domain = cls._edi_sync_domain
        if domain is None and cls._edi_sync_target is not None:
            domain = getattr(cls._fields[cls._edi_sync_target], "domain", None)
        cls._edi_sync_domain_call = (
            domain if callable(domain) else (lambda self: domain) if domain else (lambda self: [])
        )

    @api.model
    def precache_targets(self, targets):
        """Precache associated target records"""
        targets.mapped(self._edi_sync_via)

    def precache(self):
        """Precache associated records"""
        super().precache()
        self.precache_targets(self.mapped(self._edi_sync_target))

    @api.model
    def targets_by_key(self, vlist):
        """Construct lookup cache of target records indexed by key field"""
        Target = self.browse()[self._edi_sync_target].with_context(active_test=False)
        key = self._edi_sync_via
        targets = Target.search(
            expression.AND(
                [[(key, "in", [x["name"] for x in vlist])], self._edi_sync_domain_call()]
            )
        )
        self.precache_targets(targets)
        return {
            k: v.with_prefetch(targets._prefetch_ids).ensure_one() for k, v in targets.groupby(key)
        }

    @api.model
    def target_values(self, record_vals):
        """Construct target model field value dictionary

        Must return a dictionary that can be passed to
        :meth:`~odoo.models.Model.create` or
        :meth:`~odoo.models.Model.write` in order to create or update
        a record within the target model.
        """
        target_vals = {
            self._edi_sync_via: record_vals["name"],
        }
        return target_vals

    def _record_values(self):
        """Reconstruct record field value dictionary

        Reconstruct the record field value dictionary that would have
        been used at the point of comparison against an existing
        target record.

        This method exists to ensure that the dictionary used for
        comparison against existing target records is the same
        dictionary that is eventually used to create or update the
        target record.
        """
        self.ensure_one()
        record_vals = self.copy_data()[0]
        del record_vals["doc_id"]
        del record_vals[self._edi_sync_target]
        return record_vals

    @api.model
    def check_clear_cache(self, threshold, value):
        """Check if cache has to be invalidated from the threshold, where 0 means
        disabled."""
        if threshold and threshold <= value:
            value = 0
            self.invalidate_cache()

        return value

    @api.model
    def prepare(self, doc, vlist):
        """Prepare records"""
        super().prepare(doc, self.elide(doc, vlist))

    @api.model
    def elide(self, doc, vlist):
        """Elide records that would not result in a modification

        Filters the iterable ``vlist`` of value dictionaries to elide
        any entries that would not result in a modification to the
        corresponding target Odoo record.

        The result is that any EDI records that would not result in a
        modification to the corresponding target Odoo record will be
        automatically elided from the document.

        After elision has completed, :meth:`~.matched` will be called
        with a list of the matched target records (if any).  This
        allows subclasses such as ``edi.record.sync.active`` to
        perform further processing (e.g. automatically deactivating
        any unmatched records).

        Note that the iterable ``vlist`` may choose to call
        :meth:`~.no_record_values` to indicate that the iterable is
        unimplemented; in this case the call to :meth:`~.matched` will
        be bypassed.
        """
        # pylint: disable=too-many-locals

        # Get target model
        Target = self.browse()[self._edi_sync_target]
        matched_ids = set()

        # Construct comparator for target model
        comparator = Comparator(Target, self.env)

        # Construct produced values cache for deduplication
        produced = set() if self._edi_sync_dedupe else None

        # Initialise statistics
        total = 0
        count = 0
        clear_cache_count = 0
        stats = self.statistics()

        # Process records in batches for efficiency
        for r, vbatch in batched(vlist, self.BATCH_SIZE):

            _logger.info("%s preparing %s %d-%d", doc.name, self._name, r[0], r[-1])
            len_r = len(r)
            total += len_r
            clear_cache_count += len_r

            # Add EDI lookup relationship target IDs where known
            self._add_edi_relates_vlist(vbatch)

            # Look up existing target records
            targets_by_key = self.targets_by_key(vbatch)

            # Add to list of matched target record IDs
            matched_ids |= set(x.id for x in targets_by_key.values())

            # Create EDI records
            for record_vals in vbatch:

                # Look up existing target record (if any)
                target = targets_by_key.get(record_vals["name"])
                if target:

                    # Elide EDI records that would not change the target record
                    target_vals = self.target_values(record_vals)
                    if all(comparator[k](target[k], v) for k, v in target_vals.items()):
                        continue

                    # Add target to EDI record
                    record_vals[self._edi_sync_target] = target.id

                # Elide EDI records that are duplicates of earlier records
                if produced is not None:
                    frozen_record_vals = frozenset((k, v) for k, v in record_vals.items() if not isinstance(v, models.NewId))
                    if frozen_record_vals in produced:
                        continue
                    produced.add(frozen_record_vals)

                # Create EDI record
                count += 1
                yield record_vals
            clear_cache_count = self.check_clear_cache(self.CLEAR_CACHE_PREPARE, clear_cache_count)

        # Process all matched target records
        self.matched(doc, Target.browse(matched_ids))

        # Log statistics
        stats.stop()
        excess = stats.count - count
        _logger.info(
            "%s prepared %s elided %d of %d, %d excess queries",
            doc.name,
            self._name,
            (total - count),
            total,
            excess,
        )
        if excess >= total and total > PRECACHE_WARNING_THRESHOLD:
            _logger.warning(
                "%s missing precaching for %s: %d records, %d " "excess queries",
                doc.name,
                self._name,
                total,
                excess,
            )

    @api.model
    def matched(self, _doc, _targets):
        """Process matched target records"""
        pass

    def execute(self):
        """Execute records"""
        super().execute()

        # Identify containing document
        doc = self.mapped("doc_id")

        # Get target model
        target = self._edi_sync_target
        Target = self.browse()[target]

        # Identify any missing existing target records
        new = self.filtered(lambda x: not x[target])
        for r, batch in new.batched(self.BATCH_SIZE):
            _logger.info(
                "%s rechecking %s %d-%d of %d", doc.name, Target._name, r[0], r[-1], len(new)
            )
            targets_by_key = self.targets_by_key(batch)
            for rec in batch:
                if rec.name in targets_by_key:
                    rec[target] = targets_by_key[rec.name]

        # Process records in order of lookup relationship readiness
        remaining = self
        offset = 0
        clear_cache_count = 0
        while remaining:

            # Identify records for which all lookup relationships are ready
            ready = remaining._add_edi_relates(required=False)
            if not ready:
                ready = remaining._add_edi_relates(required=True)
            if not ready:
                # No more progress can be made. Do not raise an error, since
                # fail_fast must be off here, otherwise
                # _add_edi_relates(required=True) would have already raised one.
                break
            remaining -= ready

            # Update existing target records
            existing = ready.filtered(lambda x: x[target])
            for r, batch in existing.batched(self.BATCH_UPDATE):
                batch.precache()
                count = len(r)
                _logger.info(
                    "%s updating %s %d-%d of %d",
                    doc.name,
                    Target._name,
                    offset,
                    (offset + count - 1),
                    len(self),
                )
                with self.statistics() as stats:
                    vals_list = [rec.target_values(rec._record_values())
                                 for rec in batch]
                    if doc.fail_fast:
                        for rec, vals in zip(batch, vals_list):
                            rec[target].write(vals)
                    else:
                        for rec, vals in zip(batch, vals_list):
                            try:
                                # We use a savepoint here to handle the case where
                                # vals violate an api.constrains on the target.
                                # These constraints are checked after updates are
                                # sent to the database, so the offending change
                                # must be rolled back for the affected object.
                                with self.env.cr.savepoint():
                                    rec[target].write(vals)
                            except ValidationError as ex:
                                rec[target].invalidate_cache()
                                rec.error = ex.name
                                _logger.exception('Failed to update for %r, %s', rec, rec.name)
                    self.recompute()
                _logger.info("%s updated %s %d-%d in %.2fs, %d excess queries",
                             doc.name, Target._name, offset,
                             (offset + count - 1), stats.elapsed,
                             (stats.count - count))
                offset += count
                clear_cache_count += count
                clear_cache_count = self.check_clear_cache(self.CLEAR_CACHE_EXECUTE, clear_cache_count)

            # Create new target records
            new = ready.filtered(lambda x: not x[target])
            for r, batch in new.batched(self.BATCH_CREATE):
                batch.precache()
                count = len(r)
                _logger.info(
                    "%s creating %s %d-%d of %d",
                    doc.name,
                    Target._name,
                    offset,
                    (offset + count - 1),
                    len(self),
                )
                with self.statistics() as stats:
                    vals_list = list(
                        self.add_edi_defaults(
                            Target, (rec.target_values(rec._record_values()) for rec in batch)
                        )
                    )
                    if doc.fail_fast:
                        targets = [Target.create(vals) for vals in vals_list]
                    else:
                        targets = []
                        bad_recs = batch.browse()
                        for rec, vals in zip(batch, vals_list):
                            try:
                                instance = Target.create(vals)
                                targets.append(instance)
                            except ValidationError as ex:
                                _logger.exception('Failed to create for %r, %s', rec, rec.name)
                                rec.error = ex.name
                                bad_recs |= rec
                        if bad_recs:
                            batch -= bad_recs

                    for rec, created in zip(batch, targets):
                        rec[target] = created
                    self.recompute()
                _logger.info(
                    "%s created %s %d-%d in %.2fs, %d excess queries",
                    doc.name,
                    Target._name,
                    offset,
                    (offset + count - 1),
                    stats.elapsed,
                    (stats.count - 2 * count),
                )
                offset += count
                clear_cache_count += count
                clear_cache_count = self.check_clear_cache(self.CLEAR_CACHE_EXECUTE, clear_cache_count)


class EdiDeactivatorRecord(models.AbstractModel):
    """EDI deactivator record

    This is the base model for EDI records that simply deactivate
    records in a target model.  Each row represents an Odoo record
    that will be deactivated when the document is executed.

    Derived models must override the comodel name for ``target_id``.
    """

    _edi_deactivator_name = "name"
    """EDI deactivator target name field

    This is the name of the field within the target Odoo model used to
    provide a name for the corresponding EDI record.  Defaults to
    ``name``.
    """

    _name = "edi.record.deactivator"
    _inherit = "edi.record"
    _description = "EDI Deactivator Record"

    target_id = fields.Many2one(
        "_unknown", string="Target", required=True, readonly=True, index=True
    )

    def execute(self):
        """Execute records"""
        super().execute()
        self.mapped("target_id").write({"active": False})


class EdiActiveSyncRecord(models.AbstractModel):
    """EDI active synchronizer record

    This is an extension of an EDI synchronizer record to handle the
    active status of a target record.
    """

    _edi_sync_deactivator = None
    """EDI record model for target deactivation records"""

    _name = "edi.record.sync.active"
    _inherit = "edi.record.sync"
    _description = "EDI Active Synchronizer Record"

    @api.model
    def target_values(self, record_vals):
        """Construct target model field value dictionary"""
        target_vals = super().target_values(record_vals)
        target_vals.update(
            {
                "active": True,
            }
        )
        return target_vals

    @api.model
    def matched(self, doc, targets):
        """Process matched target records"""
        if self._edi_sync_deactivator is not None:
            Deactivator = self.env[self._edi_sync_deactivator]
            unmatched = targets.search(self._edi_sync_domain_call()) - targets
            Deactivator.prepare(
                doc,
                (
                    {
                        "target_id": target.id,
                        "name": target[Deactivator._edi_deactivator_name],
                    }
                    for target in unmatched
                ),
            )
