# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Module containing Document model."""

from sqlalchemy import orm

from ggrc import db
from ggrc.access_control.roleable import Roleable
from ggrc.builder import simple_property
from ggrc.fulltext.mixin import Indexed
from ggrc.models import exceptions, comment
from ggrc.models import reflection
from ggrc.models import mixins
from ggrc.models.deferred import deferred
from ggrc.models.mixins import before_flush_handleable as bfh
from ggrc.models.mixins.base import Identifiable
from ggrc.models.mixins.statusable import Statusable
from ggrc.models.mixins.with_relationship_handler import WithRelationshipHandler
from ggrc.models.relationship import Relatable
from ggrc.models.relationship import Relationship
from ggrc.services import signals
from ggrc.utils import referenced_objects


class Document(Roleable, Relatable, mixins.Titled,
               bfh.BeforeFlushHandleable, mixins.Slugged, Indexed, Statusable,
               mixins.WithLastDeprecatedDate, comment.Commentable,
               WithRelationshipHandler,
               Identifiable, db.Model):
  """Document model."""
  __tablename__ = 'documents'

  _title_uniqueness = False

  link = deferred(db.Column(db.String, nullable=False), 'Document')
  description = deferred(db.Column(db.Text, nullable=False, default=u""),
                         'Document')
  URL = "URL"
  FILE = "FILE"
  REFERENCE_URL = "REFERENCE_URL"
  VALID_DOCUMENT_KINDS = [URL, FILE, REFERENCE_URL]

  START_STATE = 'Active'
  DEPRECATED = 'Deprecated'

  VALID_STATES = (START_STATE, DEPRECATED, )

  kind = deferred(db.Column(db.Enum(*VALID_DOCUMENT_KINDS),
                            default=URL,
                            nullable=False),
                  "Document")
  source_gdrive_id = deferred(db.Column(db.String, nullable=False,
                                        default=u""),
                              'Document')

  gdrive_id = deferred(db.Column(db.String, nullable=False,
                                 default=u""),
                       'Document')

  _api_attrs = reflection.ApiAttributes(
      'title',
      'description',
      'status',
      reflection.Attribute('link', update=False),
      reflection.Attribute('kind', update=False),
      reflection.Attribute('source_gdrive_id', update=False),
      reflection.Attribute('gdrive_id', create=False, update=False),
      reflection.Attribute('parent_obj', read=False, update=False),
      reflection.Attribute('is_uploaded', read=False, update=False),
  )

  _fulltext_attrs = [
      'title',
      'link',
      'description',
      'kind',
      'status'
  ]

  _sanitize_html = [
      'title',
      'description',
  ]

  _aliases = {
      'title': 'Title',
      'link': 'Link',
      'description': 'description',
      'kind': 'type',
  }

  ALLOWED_PARENTS = {'Control', 'Issue', 'RiskAssessment'}

  FILE_NAME_SEPARATOR = '_ggrc'

  @orm.validates('kind')
  def validate_kind(self, key, kind):
    """Returns correct option, otherwise rises an error"""
    if kind is None:
      kind = self.URL
    if kind not in self.VALID_DOCUMENT_KINDS:
      raise exceptions.ValidationError(
          "Invalid value for attribute {attr}. "
          "Expected options are `{url}`, `{kind}`, `{reference_url}`".
          format(
              attr=key,
              url=self.URL,
              kind=self.FILE,
              reference_url=self.REFERENCE_URL
          )
      )
    return kind

  @classmethod
  def indexed_query(cls):
    return super(Document, cls).indexed_query().options(
        orm.Load(cls).undefer_group(
            "Document_complete",
        ),
    )

  def _display_name(self):
    result = self.title
    if self.kind == Document.FILE:
      result = self.link + ' ' + self.title
    return result

  def log_json(self):
    tmp = super(Document, self).log_json()
    tmp['type'] = "Document"
    return tmp

  @simple_property
  def is_uploaded(self):
    """This flag is used to know if file uploaded from a local user folder.

    In that case we need just rename file, not copy.
    """
    return self._is_uploaded if hasattr(self, '_is_uploaded') else False

  @is_uploaded.setter
  def is_uploaded(self, value):
    # pylint: disable=attribute-defined-outside-init
    self._is_uploaded = value

  @simple_property
  def parent_obj(self):
    return self._parent_obj

  @parent_obj.setter
  def parent_obj(self, value):
    # pylint: disable=attribute-defined-outside-init
    self._parent_obj = value

  def _get_parent_obj(self):
    """Get parent object specified"""
    if 'id' not in self._parent_obj:
      raise exceptions.ValidationError('"id" is mandatory for parent_obj')
    if 'type' not in self._parent_obj:
      raise exceptions.ValidationError(
          '"type" is mandatory for parent_obj')
    if self._parent_obj['type'] not in self.ALLOWED_PARENTS:
      raise exceptions.ValidationError(
          'Allowed types are: {}.'.format(', '.join(self.ALLOWED_PARENTS)))

    parent_type = self._parent_obj['type']
    parent_id = self._parent_obj['id']
    obj = referenced_objects.get(parent_type, parent_id)

    if not obj:
      raise ValueError(
          'Parent object not found: {type} {id}'.format(type=parent_type,
                                                        id=parent_id))
    return obj

  @staticmethod
  def _build_file_name_postfix(parent_obj):
    """Build postfix for given parent object"""
    postfix_parts = [Document.FILE_NAME_SEPARATOR, parent_obj.slug]

    related_snapshots = parent_obj.related_objects(_types=['Snapshot'])
    related_snapshots = sorted(related_snapshots, key=lambda it: it.id)

    slugs = (sn.revision.content['slug'] for sn in related_snapshots if
             sn.child_type == parent_obj.assessment_type)

    postfix_parts.extend(slugs)
    postfix_sting = '_'.join(postfix_parts).lower()

    return postfix_sting

  def _build_relationship(self, parent_obj):
    """Build relationship between document and documentable object"""
    from ggrc.models import relationship
    rel = relationship.Relationship(
        source=parent_obj,
        destination=self
    )
    db.session.add(rel)

  def _update_fields(self, link):
    """Update fields of document with values of the copied file"""
    self.gdrive_id = self.source_gdrive_id
    self.link = link
    self.kind = Document.FILE

  @staticmethod
  def _get_folder(parent):
    return parent.folder if hasattr(parent, 'folder') else ''

  def _process_gdrive_business_logic(self):
    """Handles gdrive business logic

    If parent_obj specified => add file to parent folder
    If parent_obj not specified => get file link
    """
    if self.is_with_parent_obj():
      parent = self._get_parent_obj()
      if self.kind == Document.FILE and self.source_gdrive_id:
        self.add_gdrive_file_folder(parent)
      self._build_relationship(parent)
      self._parent_obj = None
    elif self.kind == Document.FILE and self.source_gdrive_id and not self.link:
      self.gdrive_id = self.source_gdrive_id
      from ggrc.gdrive.file_actions import get_gdrive_file_link
      self.link = get_gdrive_file_link(self.source_gdrive_id)

  def add_gdrive_file_folder(self, documentable_obj):
    """Add file to parent folder if exists"""

    folder_id = self._get_folder(documentable_obj)
    file_id = self.source_gdrive_id
    from ggrc.gdrive import file_actions
    if folder_id:
      file_link = file_actions.add_gdrive_file_folder(folder_id, file_id)
    else:
      file_link = file_actions.get_gdrive_file_link(file_id)
    self._update_fields(file_link)

  def is_with_parent_obj(self):
    return bool(hasattr(self, '_parent_obj') and self._parent_obj)

  def handle_before_flush(self):
    """Handler that called  before SQLAlchemy flush event"""
    self._process_gdrive_business_logic()

  def handle_relationship_created(self, target):
    if (self.kind == Document.FILE and
            target and hasattr(target, 'folder') and target.folder):
      from ggrc.gdrive import file_actions
      file_actions.add_gdrive_file_folder(self.gdrive_id, target.folder)

  def handle_relationship_deleted(self, target):
    if (self.kind == Document.FILE and
            target and hasattr(target, 'folder') and target.folder):
      from ggrc.gdrive import file_actions
      file_actions.remove_gdrive_file_folder(self.gdrive_id, target.folder)
