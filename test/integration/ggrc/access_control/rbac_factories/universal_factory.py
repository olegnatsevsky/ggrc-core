# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Document RBAC Factory."""

from ggrc import db
from ggrc.models import all_models
from integration.ggrc import Api, generator
from integration.ggrc.access_control.rbac_factories import base
from integration.ggrc.models import factories
from integration.ggrc.models.factories import get_model_factory

FACTORIES_MAPPING = {
    "Control": factories.ControlFactory,
    "Standard": factories.StandardFactory,
    "Program": factories.ProgramFactory
}


class UniversalRBACFactory(base.BaseRBACFactory):
  """Universal RBAC factory class.

  Can be used in 'one rank' tests
  """
  # pylint: disable=too-many-instance-attributes

  def __init__(self, user_id, acr, parent=None):
    """Set up objects for permission tests.

    Args:
        user_id: Id of user under which all operations will be run.
        acr: Instance of ACR that should be assigned for tested user.
        parent: Model name in scope of which objects should be set up.
    """
    self.api = Api()
    self.objgen = generator.ObjectGenerator()
    self.objgen.api = self.api

    self.acr = acr
    self.user_id = user_id
    self.parent_name = parent
    self.document_id = None
    self.parent = None
    self.parent_id = None
    self.setup_models(self.parent_name)
    self.set_user(user_id)

  def set_user(self, user_id):
    """Set user to send requests"""
    if self.user_id:
      user = all_models.Person.query.get(user_id)
      self.api.set_user(user)

  def setup_models(self, parent_name):
    """Setup document, parent, relationship"""
    with factories.single_commit():
      self.parent = get_model_factory(parent_name)()
      self.parent_id = self.parent.id
      self.parent_name = parent_name
      self.assign_person(self.parent, self.acr, self.user_id)

  def _setup_document(self):
    """Crate and map document"""
    with factories.single_commit():
      document = factories.DocumentReferenceUrlFactory()
      parent = db.session.query(self.parent.__class__).get(self.parent_id)
      factories.RelationshipFactory(source=parent, destination=document)
    return document.id

  def _setup_comment(self):
    """Crate and map comment"""
    with factories.single_commit():
      comment = factories.CommentFactory(description="Hey!")
      parent = db.session.query(self.parent.__class__).get(self.parent_id)
      factories.RelationshipFactory(source=parent, destination=comment)
    return comment.id

  def read_parent(self):
    """Can Read parent info."""
    res = self.api.get(self.parent, self.parent_id)
    return res

  def create_and_map_document(self):
    """Create and map document object to parent."""
    admin_acr_id = all_models.AccessControlRole.query.filter_by(
        name="Admin",
        object_type="Document",
    ).one().id

    _, document = self.objgen.generate_object(
        all_models.Document, {
            "link":
            factories.random_str(),
            "title":
            factories.random_str(),
            "context":
            None,
            "access_control_list": [
                {
                    "ac_role_id": admin_acr_id,
                    "person": {
                        "id": self.user_id,
                        "type": "Person",
                    }
                }
            ],
        }
    )
    parent = db.session.query(self.parent.__class__).get(self.parent_id)
    return self.objgen.generate_relationship(
        source=document, destination=parent
    )[0]

  def read_document(self):
    """Read existing Document object."""
    doc_id = self._setup_document()
    res = self.api.get(all_models.Document, doc_id)
    return res

  def update_document(self):
    """Update title of existing Document object."""
    doc_id = self._setup_document()
    document = all_models.Document.query.get(doc_id)
    return self.api.put(document, {"title": factories.random_str()})

  def delete_document(self):
    """Delete Document object."""
    doc_id = self._setup_document()
    document = all_models.Document.query.get(doc_id)
    return self.api.delete(document)

  def create_and_map_comment(self):
    """Create new Comment object and map to parent."""
    _, comment = self.objgen.generate_object(
        all_models.Comment, {
            "description": factories.random_str(),
            "context": None,
        }
    )
    parent = db.session.query(self.parent.__class__).get(self.parent_id)
    return self.objgen.generate_relationship(
        source=parent, destination=comment
    )[0]

  def read_comment(self):
    """Read existing Comment object."""
    comment_id = self._setup_comment()
    res = self.api.get(all_models.Comment, comment_id)
    return res

  def create_and_map_document_comment(self):
    """Map new comment to document."""
    doc_id = self._setup_document()
    _, comment = self.objgen.generate_object(
        all_models.Comment, {
            "description": factories.random_str(),
            "context": None,
        }
    )
    document = all_models.Document.query.get(doc_id)
    return self.objgen.generate_relationship(
        source=document, destination=comment
    )[0]

  def read_document_comment(self):
    """Read comments mapped to document"""
    doc_id = self._setup_document()
    document = all_models.Document.query.get(doc_id)
    with factories.single_commit():
      comment = factories.CommentFactory(description=factories.random_str())
      factories.RelationshipFactory(source=document, destination=comment)

    query_request_data = [
        {
            "fields": [],
            "filters": {
                "expression": {
                    "object_name": "Document",
                    "op": {
                        "name": "relevant"
                    },
                    "ids": [document.id]
                }
            },
            "object_name": "Comment",
        }
    ]

    response = self.api.send_request(
        self.api.client.post, data=query_request_data, api_link="/query"
    )
    return response
