# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

""" Module for WithEvidence mixin."""
from sqlalchemy import orm, case, and_, literal

from ggrc import db
from ggrc.fulltext.attributes import MultipleSubpropertyFullTextAttr
from sqlalchemy.ext.declarative import declared_attr

from ggrc.models import reflection
from ggrc.models.evidence import Evidence
from ggrc.models.relationship import Relationship


class WithEvidence(object):
  """WithEvidence mixin."""

  _include_links = []

  _fulltext_attrs = [
      MultipleSubpropertyFullTextAttr('evidences_file', 'evidences_file',
                                      ['title', 'link']),
      MultipleSubpropertyFullTextAttr('evidences_url', 'evidences_url',
                                      ['link'])
  ]

  _aliases = {
    "evidences_url": {
      "display_name": "Evidence URL",
      "type": reflection.AttributeInfo.Type.SPECIAL_MAPPING,
      "description": "New line separated list of URLs.",
    },

    "evidences_file": {
      "display_name": "Evidence File",
      "type": reflection.AttributeInfo.Type.SPECIAL_MAPPING,
      "description": (
        "New line separated list of evidence links and "
        "titles.\nExample:\n\nhttp://my.gdrive.link/file "
        "Title of the evidence link"
      ),
    }
  }

  @declared_attr
  def evidences(cls):
    """Return evidences related for that instance."""
    evidence_id = case(
        [
            (
                Relationship.destination_type == "Evidence",
                Relationship.destination_id,
            ),
            (
                Relationship.source_type == "Evidence",
                Relationship.source_id,
            ),
        ],
        else_=literal(False)
    )
    with_evidence_obj_id = case(
        [
            (
                Relationship.destination_type == "Evidence",
                Relationship.source_id
            ),
            (
                Relationship.source_type == "Evidence",
                Relationship.destination_id,
            ),
        ],
        else_=literal(False)
    )
    with_evidence_obj_type = case(
        [
            (
                Relationship.destination_type == "Evidence",
                Relationship.source_type
            ),
            (
                Relationship.source_type == "Evidence",
                Relationship.destination_type,
            ),
        ],
    )
    return db.relationship(
        Evidence,
        # at first we check is documentable_id not False (it return id in fact)
        # after that we can compare values.
        # this is required for saving logic consistancy
        # case return 2 types of values BOOL(false) and INT(id) not Null
        primaryjoin=lambda: and_(with_evidence_obj_id, cls.id == with_evidence_obj_id),
        secondary=Relationship.__table__,
        # at first we check is document_id not False (it return id in fact)
        # after that we can compare values.
        # this is required for saving logic consistancy
        # case return 2 types of values BOOL(false) and INT(id) not Null
        secondaryjoin=lambda: and_(evidence_id, Evidence.id == evidence_id,
                                   with_evidence_obj_type == cls.__name__),
        viewonly=True,
    )

  def get_evidences_by_kind(self, kind):
    return [e for e in self.evidences
            if e.kind == kind]

  @property
  def evidences_url(self):
    return self.get_evidences_by_kind(Evidence.URL)

  @property
  def evidences_file(self):
    return self.get_evidences_by_kind(Evidence.FILE)

  @classmethod
  def eager_query(cls):
    """Eager query classmethod."""
    return cls.eager_inclusions(
        super(WithEvidence, cls).eager_query(),
      WithEvidence._include_links,
    ).options(
        orm.subqueryload(
            'evidences',
        ).undefer_group(
            'Evidence_complete',
        ),
    )

  @staticmethod
  def _log_evidences(evidences):
    """Returns serialization of the given docs"""
    return [e.log_json() for e in evidences if e]

  def log_json(self):
    """Serialize to JSON"""
    # This query is required to refresh related documents collection after
    # they were mapped to an object. Otherwise python uses cached value,
    # which might not contain newly created documents.
    out_json = super(WithEvidence, self).log_json()
    out_json['evidences_url'] = self._log_evidences(self.evidences_url)
    out_json['evidences_file'] = self._log_evidences(self.evidences_file)
    return out_json

  @classmethod
  def indexed_query(cls):
    return super(WithEvidence, cls).indexed_query().options(
        orm.subqueryload("evidences").undefer_group("Evidence_complete"),
    )
