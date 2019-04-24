# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Module for integration tests for Relationship."""

import json

import ddt

from ggrc.models import all_models
from ggrc.models.exceptions import ValidationError

from integration.ggrc import TestCase
from integration.ggrc import api_helper
from integration.ggrc.models import factories


@ddt.ddt
class TestRelationship(TestCase):
  """Integration test suite for Relationship."""
  # pylint: disable=invalid-name

  def setUp(self):
    """Create a Person, an Assessment, prepare a Relationship json."""
    super(TestRelationship, self).setUp()
    self.api = api_helper.Api()
    self.client.get("/login")
    self.person = factories.PersonFactory()
    self.assessment = factories.AssessmentFactory()

  HEADERS = {
      "Content-Type": "application/json",
      "X-requested-by": "GGRC",
  }
  REL_URL = "/api/relationships"

  @staticmethod
  def build_relationship_json(source, destination):
    """Builds relationship create request json."""
    return json.dumps([{
        "relationship": {
            "source": {"id": source.id, "type": source.type},
            "destination": {"id": destination.id, "type": destination.type},
            "context": {"id": None},
        }
    }])

  def test_changing_log_on_doc_change(self):
    """Changing object documents should generate new object revision."""
    url_link = u"www.foo.com"
    with factories.single_commit():
      control = factories.ControlFactory()
      url = factories.DocumentReferenceUrlFactory(link=url_link)

    def get_revisions():
      return all_models.Revision.query.filter(
          all_models.Revision.resource_id == control.id,
          all_models.Revision.resource_type == control.type,
      ).order_by(
          all_models.Revision.id.desc()
      ).all()

    # attach an url to a control
    revisions = get_revisions()
    count = len(revisions)
    response = self.client.post(
        self.REL_URL,
        data=self.build_relationship_json(control, url),
        headers=self.HEADERS)
    self.assert200(response)

    relationship = all_models.Relationship.query.get(
        response.json[0][-1]["relationship"]["id"])

    # check if a revision was created and contains the attached url
    revisions = get_revisions()
    self.assertEqual(count + 1, len(revisions))
    url_list = revisions[0].content.get("documents_reference_url") or []
    self.assertEqual(1, len(url_list))
    self.assertIn("link", url_list[0])
    self.assertEqual(url_link, url_list[0]["link"])

    # now test whether a new revision is created when url is unmapped
    self.assert200(self.api.delete(relationship))

    revisions = get_revisions()
    self.assertEqual(count + 2, len(revisions))
    url_list = revisions[0].content.get("documents_reference_url") or []
    self.assertEqual(url_list, [])

  def test_relationship_disallowed_type(self):
    """Validation fails when source-destination are snapshottable."""
    audit = factories.AuditFactory()
    snapshottable = factories.ControlFactory()

    ctrl_revision = all_models.Revision.query.filter(
        all_models.Revision.resource_id == snapshottable.id,
        all_models.Revision.resource_type == snapshottable.type,
    ).first()
    snapshot = factories.SnapshotFactory(
        parent=audit,
        revision_id=ctrl_revision.id,
        child_type=snapshottable.type,
        child_id=snapshottable.id,
    )
    with self.assertRaises(ValidationError):
      factories.RelationshipFactory(source=snapshottable, destination=snapshot)
    with self.assertRaises(ValidationError):
      factories.RelationshipFactory(source=snapshot, destination=snapshottable)

  def test_relationship_validation(self):
    """Test validator that forbid creation of Relationship with the same object
    as source and destination"""
    response = self.client.post(
        self.REL_URL,
        data=self.build_relationship_json(self.assessment, self.assessment),
        headers=self.HEADERS)
    self.assert400(response)
    self.assertEqual(response.json[0][1],
                     "The mapping of object on itself is not possible")
