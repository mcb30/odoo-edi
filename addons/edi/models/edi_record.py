"""EDI records"""

import logging
from operator import itemgetter
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

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

    def __init__(self, key, target, via=None):
        self.key = key
        self.target = target
        self.via = via if via else key

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

    _edi_relates = ()
    """EDI lookup relationships"""

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
                rel = EdiLookupRelationship(name, target, via)
                cls._edi_relates.append(rel)

    @api.multi
    def _add_edi_relates(self):
        """Add EDI lookup relationship target IDs to records

        Fill in any missing target IDs based on the EDI lookup
        relationships, where possible.
        """
        Record = self.browse()
        doc = self.mapped('doc_id')
        for rel in self._edi_relates:
            # pylint: disable=cell-var-from-loop

            # Find records missing a target, if any
            missing = self.filtered(lambda x: x[rel.key] and not x[rel.target])

            # Process records in batches to minimise database lookups
            keygetter = itemgetter(rel.key)
            for r, batch in missing.batched(self.BATCH_SIZE):
                _logger.info(_("%s recording %s.%s %d-%d"),
                             doc.name, self._name, rel.target, r[0], r[-1])

                # Search for target records by key
                Target = Record[rel.target]
                targets = Target.search(
                    [(rel.via, 'in', list(set(keygetter(x) for x in batch)))]
                )
                targets_by_key = {x[rel.via]: x for x in targets}

                # Update target fields
                for key, recs in batch.groupby(keygetter):
                    target = targets_by_key.get(key)
                    if target:
                        recs.write({rel.target: target.id})
                    else:
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
        for rel in self._edi_relates:
            # pylint: disable=cell-var-from-loop

            # Find values missing a target, if any
            missing = [x for x in vlist if rel.target not in x]
            if not missing:
                continue

            # Search for target records by key
            targets = self.browse()[rel.target].search(
                [(rel.via, 'in', list(set(x[rel.key] for x in missing)))]
            )
            targets_by_key = {x[rel.via]: x for x in targets}

            # Add target values where known
            for vals in missing:
                target = targets_by_key.get(vals[rel.key])
                if target:
                    vals[rel.target] = target.id

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
        self._add_edi_relates()
