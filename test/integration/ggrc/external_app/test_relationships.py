# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Module for integration tests for Relationship."""

import json
import unittest

import ddt
import mock
import sqlalchemy as sa

from ggrc.models import all_models, Relationship

from integration.ggrc import TestCase, READONLY_MAPPING_PAIRS
from integration.ggrc import api_helper
from integration.ggrc.external_app.external_api_helper import ExternalApiClient
from integration.ggrc.models import factories
from integration.ggrc.generator import ObjectGenerator


@ddt.ddt
class TestExternalRelationship(TestCase):
  """Integration test suite for External Relationship."""

  # pylint: disable=invalid-name

  def setUp(self):
    """Init API helper"""
    super(TestExternalRelationship, self).setUp()
    self.object_generator = ObjectGenerator()
    self.ext_api = ExternalApiClient()

    self.client.get("/login")
    self.api = api_helper.Api()

  REL_URL = "/api/relationships"
  UNMAP_ENDPOINT_URL = "/api/relationships/unmap"

  @staticmethod
  def build_relationship_data(source, destination, is_external):
    """Builds relationship create request json."""
    return [
        {
            "relationship": {
                "source": {
                    "id": source.id,
                    "type": source.type
                },
                "destination": {
                    "id": destination.id,
                    "type": destination.type
                },
                "context": {
                    "id": None
                },
                "is_external": is_external
            }
        }
    ]

  @staticmethod
  def create_relationship(source, destination, is_external, user):
    """Creates relationship in database with given params."""
    return factories.RelationshipFactory(
        source=source,
        destination=destination,
        is_external=is_external,
        modified_by_id=user.id,
    )

  def test_create_ext_user_ext_relationship(self):
    """Validation external app user creates external relationship."""
    with factories.single_commit():
      product = factories.ProductFactory()
      system = factories.SystemFactory()
    response = self.ext_api.post(
        url=self.REL_URL,
        data=self.build_relationship_data(product, system, True)
    )
    self.assert200(response)

    relationship = all_models.Relationship.query.get(
        response.json[0][-1]["relationship"]["id"]
    )
    self.assertEqual(relationship.source_type, "Product")
    self.assertEqual(relationship.source_id, product.id)
    self.assertEqual(relationship.destination_type, "System")
    self.assertEqual(relationship.destination_id, system.id)
    self.assertTrue(relationship.is_external)
    person_ext_id = all_models.Person.query.filter_by(
        email="external_app@example.com"
    ).one().id
    self.assertEqual(relationship.modified_by_id, person_ext_id)
    self.assertIsNone(relationship.parent_id)
    self.assertIsNone(relationship.automapping_id)
    self.assertIsNone(relationship.context_id)

  @unittest.skip(
      "Need to update validation to allow update "
      "regular relationships but not to create"
  )
  def test_create_ext_user_reg_relationship(self):
    """Validation external app user creates regular relationship."""
    self.api.set_user(self.person_ext)
    with factories.single_commit():
      product = factories.ProductFactory()
      system = factories.SystemFactory()
    response = self.api.client.post(
        self.REL_URL,
        data=self.build_relationship_data(product, system, False),
        headers=self.HEADERS
    )
    self.assert400(response)
    self.assertEqual(
        response.json[0],
        [400, "External application can create only external relationships."]
    )

  def test_update_ext_user_ext_relationship(self):
    """Validation external app user updates external relationship."""

    with factories.single_commit():
      product = factories.ProductFactory()
      system = factories.SystemFactory()
      factories.RelationshipFactory(
          source=product,
          destination=system,
          is_external=True,
      )

    response = self.ext_api.post(
        url=self.REL_URL,
        data=self.build_relationship_data(product, system, True),
    )
    self.assert200(response)

    relationship = all_models.Relationship.query.get(
        response.json[0][-1]["relationship"]["id"]
    )
    self.assertEqual(relationship.source_type, "Product")
    self.assertEqual(relationship.source_id, product.id)
    self.assertEqual(relationship.destination_type, "System")
    self.assertEqual(relationship.destination_id, system.id)
    self.assertTrue(relationship.is_external)
    person_ext_id = all_models.Person.query.filter_by(
        email="external_app@example.com"
    ).one().id
    self.assertEqual(relationship.modified_by_id, person_ext_id)
    self.assertIsNone(relationship.parent_id)
    self.assertIsNone(relationship.automapping_id)
    self.assertIsNone(relationship.context_id)

  def test_update_ext_user_reg_relationship(self):
    """External app user can update regular relationship."""
    with factories.single_commit():
      product = factories.ProductFactory()
      system = factories.SystemFactory()
      factories.RelationshipFactory(
          source=product,
          destination=system,
          is_external=True,
      )

    response = self.ext_api.post(
        url=self.REL_URL,
        data=self.build_relationship_data(product, system, True)
    )
    self.assert200(response)
    self.assertEqual(response.json[0][1]["relationship"]["is_external"], True)

  def test_delete_ext_user_ext_relationship(self):
    """Validation external app user deletes external relationship."""
    with factories.single_commit():
      product = factories.ProductFactory()
      system = factories.SystemFactory()
      rel = factories.RelationshipFactory(
          source=product,
          destination=system,
          is_external=True,
      )

    response = self.ext_api.delete(rel, rel.id)
    self.assert200(response)
    relationship = all_models.Relationship.query.get(rel.id)
    self.assertIsNone(relationship)

  def test_delete_ext_user_reg_relationship(self):
    """External app user can delete regular relationship."""
    with factories.single_commit():
      product = factories.ProductFactory()
      system = factories.SystemFactory()
      rel = factories.RelationshipFactory(
          source=product,
          destination=system,
          is_external=True,
      )
    response = self.ext_api.delete(rel, rel.id)
    self.assert200(response)

  def test_update_reg_user_ext_relationship(self):
    """Validation regular app user updates external relationship."""

    _, regular_user = self.object_generator.generate_person(
        data={"email": "regular_user@example.com"}, user_role="Editor"
    )

    self.api.set_user(regular_user)
    with factories.single_commit():
      product = factories.ProductFactory()
      system = factories.SystemFactory()

      factories.RelationshipFactory(
          source=product,
          destination=system,
          is_external=True,
          modified_by_id=regular_user.id,
      )
    response = self.api.client.post(
        self.REL_URL,
        data=json.dumps(self.build_relationship_data(product, system, False)),
        headers={
            "Content-Type": "application/json",
            "X-requested-by": "GGRC",
        }
    )
    self.assert200(response)

  def test_delete_reg_user_ext_relationship(self):
    """Validation regular user deletes external relationship."""
    _, regular_user = self.object_generator.generate_person(
        data={"email": "regular_user@example.com"}, user_role="Editor"
    )
    self.api.set_user(regular_user)

    with factories.single_commit():
      product = factories.ProductFactory()
      system = factories.SystemFactory()

      rel = factories.RelationshipFactory(
          source=product,
          destination=system,
          is_external=True,
          modified_by_id=regular_user.id,
      )

    response = self.api.delete(rel)
    self.assert200(response)
    relationship = all_models.Relationship.query.get(rel.id)
    self.assertIsNone(relationship)

  @ddt.data(*READONLY_MAPPING_PAIRS)
  @ddt.unpack
  def test_local_delete_relationship_scoping_directive(self, model1, model2):
    """Test deletion of relationship between {0.__name__} and {1.__name__}"""

    _, regular_user = self.object_generator.generate_person(
        data={"email": "regular_user@example.com"}, user_role="Editor"
    )

    # Set up relationships
    with self.object_generator.api.as_external():
      _, obj1 = self.object_generator.generate_object(model1)
      _, obj2 = self.object_generator.generate_object(model2)

      _, rel = self.object_generator.generate_relationship(
          obj1, obj2, is_external=True
      )

    # check that relationship cannot be deleted by regular user
    self.api.set_user(regular_user)
    relationship = all_models.Relationship.query.get(rel.id)
    response = self.api.delete(relationship)
    self.assert400(response)

  @ddt.data(*READONLY_MAPPING_PAIRS)
  @ddt.unpack
  def test_local_create_relationship_scoping_directive(
      self, model1=all_models.KeyReport, model2=all_models.Regulation
  ):
    """Test creation of relationship between {0.__name__} and {1.__name__}"""
    # Set up relationships
    with self.object_generator.api.as_external():
      _, obj1 = self.object_generator.generate_object(model1)
      _, obj2 = self.object_generator.generate_object(model2)

    _, regular_user = self.object_generator.generate_person(
        data={"email": "regular_user@example.com"}, user_role="Editor"
    )

    self.object_generator.api.set_user(regular_user)

    response, _ = self.object_generator.generate_relationship(
        obj1, obj2, is_external=True
    )

    self.assert400(response)

  @ddt.data(*READONLY_MAPPING_PAIRS)
  @ddt.unpack
  def test_ext_create_delete_relationship_scoping_directive(
      self, model1, model2
  ):
    """Test ext user and relationship between {0.__name__} and {1.__name__}"""

    # Set up relationships
    with self.object_generator.api.as_external():
      _, obj1 = self.object_generator.generate_object(model1)
      _, obj2 = self.object_generator.generate_object(model2)

      _, rel = self.object_generator.generate_relationship(
          obj1, obj2, is_external=True
      )

      self.assertIsNotNone(rel)

    # check that external relationship can be deleted by external user
    relationship = all_models.Relationship.query.get(rel.id)
    response = self.ext_api.delete(relationship, relationship.id)
    self.assert200(response)

  def test_delete_normal_relationship(self):
    """External app can't delete normal relationships"""

    with factories.single_commit():
      issue = factories.IssueFactory()
      objective = factories.ObjectiveFactory()

      relationship = factories.RelationshipFactory(
          source=issue, destination=objective, is_external=False
      )
      relationship_id = relationship.id

    resp = self.ext_api.delete("relationship", relationship_id)
    self.assertStatus(resp, 400)

  @mock.patch("ggrc.settings.SYNC_SERVICE_APP_ID", new="sync_service")
  def test_delete_normal_relationship_sync_service(self):
    """Sync service should be able to delete normal relationships"""

    with factories.single_commit():
      first_object = factories.ProjectFactory()
      first_type = first_object.type
      first_id = first_object.id
      second_object = factories.ProgramFactory()
      second_type = second_object.type
      second_id = second_object.id

      relationship = factories.RelationshipFactory(
          source=first_object, destination=second_object, is_external=False
      )
      rel_id = relationship.id

    body = {
        "first_object_id": first_id,
        "first_object_type": first_type,
        "second_object_id": second_id,
        "second_object_type": second_type,
    }
    custom_headers = {"X-Appengine-Inbound-Appid": "sync_service"}

    self.ext_api.user_headers = custom_headers
    response = self.ext_api.post(url=self.UNMAP_ENDPOINT_URL, data=body)
    self.assert200(response)
    self.assertIsNone(all_models.Relationship.query.get(rel_id))

  def test_internal_user_request(self):
    """Test internal user has not access to endpoint."""
    self.client.get("/login")
    body = {
        "first_object_id": 1,
        "first_object_type": "Control",
        "second_object_id": 1,
        "second_object_type": "Product",
    }

    response = self.client.post(
        self.UNMAP_ENDPOINT_URL,
        content_type="application/json",
        data=json.dumps(body)
    )

    self.assertEqual(403, response.status_code)

  @ddt.data(
      "first_object_id",
      "first_object_type",
      "second_object_id",
      "second_object_type",
  )
  def test_mandatory_fields(self, field):
    """Test mandatory fields validation."""
    body = {
        "first_object_id": 1,
        "first_object_type": "Control",
        "second_object_id": 1,
        "second_object_type": "Product",
    }
    del body[field]

    response = self.ext_api.post(url=self.UNMAP_ENDPOINT_URL, data=body)

    self.assertEqual(400, response.status_code)

    expected_message = "Missing mandatory attribute: %s." % field
    actual_message = json.loads(response.data)["message"]
    self.assertEqual(expected_message, actual_message)

  @ddt.data(
      ("first_object_id", "id", "first"),
      ("first_object_type", "type", "first"),
      ("second_object_id", "id", "second"),
      ("second_object_type", "type", "second"),
  )
  @ddt.unpack
  def test_invalid_type(self, field, field_type, field_number):
    """Test field type validation."""
    body = {
        "first_object_id": 1,
        "first_object_type": "Control",
        "second_object_id": 1,
        "second_object_type": "Product",
        field: None
    }

    response = self.ext_api.post(url=self.UNMAP_ENDPOINT_URL, data=body)

    self.assertEqual(400, response.status_code)

    expected_message = "Invalid object %s for %s object." % (
        field_type, field_number
    )
    actual_message = json.loads(response.data)["message"]
    self.assertEqual(expected_message, actual_message)

  def test_unmapping(self):
    """Test field type validation."""
    with factories.single_commit():
      first_object = factories.ProjectFactory()
      first_type = first_object.type
      first_id = first_object.id
      second_object = factories.ProgramFactory()
      second_type = second_object.type
      second_id = second_object.id

      relationship_1 = factories.RelationshipFactory(
          source=first_object, destination=second_object, is_external=True
      ).id
      relationship_2 = factories.RelationshipFactory(
          source=second_object, destination=first_object, is_external=True
      ).id

    body = {
        "first_object_id": first_id,
        "first_object_type": first_type,
        "second_object_id": second_id,
        "second_object_type": second_type,
    }

    response = self.ext_api.post(url=self.UNMAP_ENDPOINT_URL, data=body)

    self.assertEqual(200, response.status_code)

    deleted_count = json.loads(response.data)["count"]
    self.assertEqual(2, deleted_count)

    remained_count = Relationship.query.filter(
        sa.or_(
            sa.and_(
                Relationship.source_type == first_type,
                Relationship.source_id == first_id,
                Relationship.destination_type == second_type,
                Relationship.destination_id == second_id
            ),
            sa.and_(
                Relationship.source_type == second_type,
                Relationship.source_id == second_id,
                Relationship.destination_type == first_type,
                Relationship.destination_id == first_id
            )
        )
    ).count()
    self.assertEqual(0, remained_count)

    self.assertEqual(None, Relationship.query.get(relationship_1))
    self.assertEqual(None, Relationship.query.get(relationship_2))
