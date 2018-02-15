# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

""" Module for docuumentable mixins."""

from sqlalchemy import orm, case, and_, literal
from sqlalchemy.ext.declarative import declared_attr

from ggrc import db
from ggrc.models import reflection
from ggrc.models.relationship import Relationship
from ggrc.models.document import Document
from ggrc.fulltext.attributes import MultipleSubpropertyFullTextAttr


class Documentable(object):
  """Documentable mixin."""

  _include_links = []

  _fulltext_attrs = [
      MultipleSubpropertyFullTextAttr('documents_file', 'documents_file',
                                      ['title', 'link']),
      MultipleSubpropertyFullTextAttr('documents_url', 'documents_url',
                                      ['link']),
      MultipleSubpropertyFullTextAttr('documents_reference_url', 'documents_reference_url',
                                      ['link']),
  ]

  @declared_attr
  def documents(cls):
    """Return documents releated for that instance."""
    document_id = case(
        [
            (
                Relationship.destination_type == "Document",
                Relationship.destination_id,
            ),
            (
                Relationship.source_type == "Document",
                Relationship.source_id,
            ),
        ],
        else_=literal(False)
    )
    documentable_id = case(
        [
            (
                Relationship.destination_type == "Document",
                Relationship.source_id
            ),
            (
                Relationship.source_type == "Document",
                Relationship.destination_id,
            ),
        ],
        else_=literal(False)
    )
    documentable_type = case(
        [
            (
                Relationship.destination_type == "Document",
                Relationship.source_type
            ),
            (
                Relationship.source_type == "Document",
                Relationship.destination_type,
            ),
        ],
    )
    return db.relationship(
        Document,
        # at first we check is documentable_id not False (it return id in fact)
        # after that we can compare values.
        # this is required for saving logic consistancy
        # case return 2 types of values BOOL(false) and INT(id) not Null
        primaryjoin=lambda: and_(documentable_id, cls.id == documentable_id),
        secondary=Relationship.__table__,
        # at first we check is document_id not False (it return id in fact)
        # after that we can compare values.
        # this is required for saving logic consistancy
        # case return 2 types of values BOOL(false) and INT(id) not Null
        secondaryjoin=lambda: and_(document_id, Document.id == document_id,
                                   documentable_type == cls.__name__),
        viewonly=True,
    )

  def get_documents_by_kind(self, kind):
    return [e for e in self.documents
            if e.kind == kind]

  @property
  def documents_url(self):
    """List of documents URL type"""
    return self.get_documents_by_kind(Document.URL)

  @property
  def documents_file(self):
    """List of documents FILE type"""
    return self.get_documents_by_kind(Document.FILE)

  @property
  def documents_reference_url(self):
    """List of documents REFERENCE_URL type"""
    return self.get_documents_by_kind(Document.REFERENCE_URL)

  @classmethod
  def eager_query(cls):
    """Eager query classmethod."""
    return cls.eager_inclusions(
        super(Documentable, cls).eager_query(),
        Documentable._include_links,
    ).options(
        orm.subqueryload(
            'documents',
        ).undefer_group(
            'Document_complete',
        ),
    )

  @staticmethod
  def _log_docs(documents):
    """Returns serialization of the given docs"""
    return [d.log_json() for d in documents if d]

  def log_json(self):
    """Serialize to JSON"""
    # This query is required to refresh related documents collection after
    # they were mapped to an object. Otherwise python uses cached value,
    # which might not contain newly created documents.
    out_json = super(Documentable, self).log_json()
    out_json["documents_url"] = self._log_docs(self.documents_url)
    out_json["documents_file"] = self._log_docs(self.documents_file)
    out_json["documents_reference_url"] = self._log_docs(self.documents_reference_url)
    return out_json

  @classmethod
  def indexed_query(cls):
    return super(Documentable, cls).indexed_query().options(
        orm.subqueryload("documents").undefer_group("Document_complete"),
    )


class PublicDocumentable(Documentable):
  _aliases = {
      "documents_url": {
          "display_name": "Document URL",
          "type": reflection.AttributeInfo.Type.SPECIAL_MAPPING,
          "description": "New line separated list of URLs.",
      },

      "documents_file": {
          "display_name": "Document File",
          "type": reflection.AttributeInfo.Type.SPECIAL_MAPPING,
          "description": (
              "New line separated list of evidence links and "
              "titles.\nExample:\n\nhttp://my.gdrive.link/file "
              "Title of the evidence link"
          ),
      },
      "documents_reference_url": {
          "display_name": "Reference URL",
          "type": reflection.AttributeInfo.Type.SPECIAL_MAPPING,
          "description": "New line separated list of Reference URLs.",
      },
  }
