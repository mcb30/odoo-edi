"""EDI synchronizer documents"""

import logging
from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.osv import expression
from ..tools import batched, Comparator

_logger = logging.getLogger(__name__)


class NoRecordValuesError(NotImplementedError):
    """Method for constructing EDI record value dictionaries is not used

    This exception can be raised by document models derived from
    ``edi.document.sync`` to indicate that the method for constructing
    EDI record value dictionaries has not been implemented and should
    not be used.

    This allows a record model derived from ``edi.record.sync`` to
    identify situations in which the document model has chosen not to
    use the convenience methods for constructing EDI record value
    dictionaries, and so abandon the record preparation without any
    side effects (such as deactivating any unmatched records).
    """
    pass


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

    _name = 'edi.document.sync'
    _inherit = 'edi.document.model'
    _description = "EDI Synchronizer Document"

    @api.model
    def no_record_values(self):
        """Indicate that this record value generator is not implemented

        This method should be called by any empty placeholder
        convenience methods for constructing EDI record value
        dictionaries (such as are typically found in the base models
        for an EDI synchronizer document type).
        """
        raise NoRecordValuesError


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

    _edi_sync_target = None
    """EDI synchronizer target field

    This is the name of the EDI record relational field mapping to the
    target Odoo record.
    """

    _edi_sync_via = 'name'
    """EDI synchronizer target model lookup key field

    This is the name of the field within the target Odoo model used to
    identify the corresponding target record.  Defaults to ``name``.
    """

    _edi_sync_domain = None
    """EDI synchronizer target domain

    This is an additional search domain applied to the target Odoo
    model when identifying the corresponding target record.
    """

    _name = 'edi.record.sync'
    _inherit = 'edi.record'
    _description = "EDI Synchronizer Record"

    _sql_constraints = [
        ('doc_name_uniq', 'unique (doc_id, name)',
         "Each synchronizer key may appear at most once per document")
    ]

    @api.model
    def _setup_complete(self):
        """Complete the model setup"""
        super()._setup_complete()
        cls = type(self)
        domain = cls._edi_sync_domain
        cls._edi_sync_domain = (
            domain if callable(domain) else
            (lambda self: domain) if domain else
            (lambda self: [])
        )

    @api.model
    def targets_by_key(self, vlist):
        """Construct lookup cache of target records indexed by key field"""
        Target = self.browse()[self._edi_sync_target].with_context(
            active_test=False
        )
        key = self._edi_sync_via
        targets = Target.search(expression.AND([
            [(key, 'in', [x['name'] for x in vlist])],
            self._edi_sync_domain()
        ]))
        return {k: v.ensure_one() for k, v in targets.groupby(key)}

    @api.model
    def target_values(self, record_vals):
        """Construct target model field value dictionary

        Must return a dictionary that can be passed to
        :meth:`~odoo.models.Model.create` or
        :meth:`~odoo.models.Model.write` in order to create or update
        a record within the target model.
        """
        target_vals = {
            self._edi_sync_via: record_vals['name'],
        }
        return target_vals

    @api.multi
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
        del record_vals['doc_id']
        del record_vals[self._edi_sync_target]
        return record_vals

    @api.model
    def prepare(self, doc, vlist):
        """Prepare records

        Accepts an EDI document ``doc`` and an iterable ``vlist``
        yielding value dictionaries that could be passed to
        :meth:`~odoo.models.Model.create` in order to create an EDI
        record.

        Any EDI records that would not result in a modification to the
        corresponding target Odoo record will be automatically elided
        from the document.
        """

        # Get target model
        Target = self.browse()[self._edi_sync_target]
        matched_ids = set()

        # Construct comparator for target model
        comparator = Comparator(Target)

        # Check for unimplemented values dictionary iterable
        try:

            # Process records in batches for efficiency
            for r, vbatch in batched(vlist, self.BATCH_SIZE):

                _logger.info(_("%s preparing %s %d-%d"),
                             doc.name, self._name, r[0], r[-1])

                # Add EDI lookup relationship target IDs where known
                self._add_edi_relates_vlist(vbatch)

                # Look up existing target records
                targets_by_key = self.targets_by_key(vbatch)

                # Add to list of matched target record IDs
                matched_ids |= set(x.id for x in targets_by_key.values())

                # Create EDI records
                for record_vals in vbatch:

                    # Omit EDI records that would not change the target record
                    target = targets_by_key.get(record_vals['name'])
                    if target:
                        target_vals = self.target_values(record_vals)
                        if all(comparator[k](target[k], v)
                               for k, v in target_vals.items()):
                            continue

                    # Create EDI record
                    record_vals['doc_id'] = doc.id
                    if target:
                        record_vals[self._edi_sync_target] = target.id
                    self.create(record_vals)

        except NoRecordValuesError:
            # Values dictionary iterable was not implemented (most
            # likely because the document model has chosen not to use
            # a convenience method): skip all further processing.
            return

        # Process all matched target records
        self.matched(doc, Target.browse(matched_ids))

    @api.model
    def matched(self, _doc, _targets):
        """Process matched target records"""
        pass

    @api.multi
    def execute(self):
        """Execute records"""
        super().execute()

        # Identify containing document
        doc = self.mapped('doc_id')

        # Get target model
        target = self._edi_sync_target
        Target = self.browse()[target].with_context(tracking_disable=True)

        # Identify any missing existing target records
        new = self.filtered(lambda x: not x[target])
        for r, batch in new.batched(self.BATCH_SIZE):
            _logger.info(_("%s rechecking %s %d-%d"),
                         doc.name, Target._name, r[0], r[-1])
            targets_by_key = self.targets_by_key(batch)
            for rec in batch:
                if rec.name in targets_by_key:
                    rec[target] = targets_by_key[rec.name]

        # Update existing target records
        existing = self.filtered(lambda x: x[target])
        for r, batch in existing.batched(self.BATCH_SIZE):
            _logger.info(_("%s updating %s %d-%d"),
                         doc.name, Target._name, r[0], r[-1])
            for rec in batch:
                target_vals = rec.target_values(rec._record_values())
                rec[target].write(target_vals)

        # Create new target records
        new = self.filtered(lambda x: not x[target])
        for r, batch in new.batched(self.BATCH_SIZE):
            _logger.info(_("%s creating %s %d-%d"),
                         doc.name, Target._name, r[0], r[-1])
            for rec in batch:
                target_vals = rec.target_values(rec._record_values())
                rec[target] = Target.create(target_vals)


class EdiDeactivatorRecord(models.AbstractModel):
    """EDI deactivator record

    This is the base model for EDI records that simply deactivate
    records in a target model.  Each row represents an Odoo record
    that will be deactivated when the document is executed.

    Derived models must override the comodel name for ``target_id``.
    """

    _edi_deactivator_name = 'name'
    """EDI deactivator target name field

    This is the name of the field within the target Odoo model used to
    provide a name for the corresponding EDI record.  Defaults to
    ``name``.
    """

    _name = 'edi.record.deactivator'
    _inherit = 'edi.record'
    _description = "EDI Deactivator Record"

    target_id = fields.Many2one('_unknown', string="Target", required=True,
                                readonly=True, index=True)

    @api.model
    def prepare(self, doc, targets):
        """Prepare records

        Accepts an EDI document ``doc`` and a list of target records
        to be deactivated.
        """
        for target in targets:
            self.create({
                'doc_id': doc.id,
                'target_id': target.id,
                'name': target[self._edi_deactivator_name],
            })

    @api.multi
    def execute(self):
        """Execute records"""
        super().execute()
        self.mapped('target_id').write({'active': False})


class EdiActiveSyncRecord(models.AbstractModel):
    """EDI active synchronizer record

    This is an extension of an EDI synchronizer record to handle the
    active status of a target record.
    """

    _edi_sync_deactivator = None
    """EDI record model for target deactivation records"""

    _name = 'edi.record.sync.active'
    _inherit = 'edi.record.sync'
    _description = "EDI Active Synchronizer Record"

    @api.model
    def target_values(self, record_vals):
        """Construct target model field value dictionary"""
        target_vals = super().target_values(record_vals)
        target_vals.update({
            'active': True,
        })
        return target_vals

    @api.model
    def matched(self, doc, targets):
        """Process matched target records"""
        if self._edi_sync_deactivator is not None:
            Deactivator = self.env[self._edi_sync_deactivator]
            unmatched = (targets.search(self._edi_sync_domain()) - targets)
            Deactivator.prepare(doc, unmatched)
