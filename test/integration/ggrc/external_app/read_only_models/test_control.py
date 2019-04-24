# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Tests for control model."""
# pylint: disable=too-many-lines

from datetime import datetime, date
import json

import ddt
import mock

from sqlalchemy.ext import associationproxy
from sqlalchemy.orm import collections

from ggrc import db
from ggrc.models import all_models
from ggrc.models.mixins import synchronizable
from ggrc.utils import user_generator
from integration.ggrc import TestCase, generator
from integration.ggrc.external_app.external_api_helper import ExternalApiClient
from integration.ggrc.models import factories
from integration.ggrc_workflows.models import factories as wf_factories
from integration.ggrc import api_helper


class TestControl(TestCase):
  """Tests for control model."""

  def setUp(self):
    """setUp, nothing else to add."""
    super(TestControl, self).setUp()
    self.api = api_helper.Api()

  def test_create_control(self):
    """Test control update with internal user."""
    response = self.api.post(all_models.Control, {"title": "new-title"})
    self.assert403(response)

    control_count = db.session.query(all_models.Control).filter(
        all_models.Control.title == "new-title").count()
    self.assertEqual(0, control_count)

  def test_update_control(self):
    """Test control update with internal user."""
    control = factories.ControlFactory()
    old_title = control.title

    response = self.api.put(control, {"title": "new-title"})
    self.assert403(response)

    control = db.session.query(all_models.Control).get(control.id)
    self.assertEqual(old_title, control.title)

  def test_delete_control(self):
    """Test control update with internal user."""
    control = factories.ControlFactory()

    response = self.api.delete(control)
    self.assert403(response)

    control = db.session.query(all_models.Control).get(control.id)
    self.assertIsNotNone(control.title)

  def test_control_read(self):
    """Test correctness of control field values on read operation."""
    control_body = {
        "title": "test control",
        "slug": "CONTROL-01",
        "kind": "test kind",
        "means": "test means",
        "verify_frequency": "test frequency",
    }
    control = factories.ControlFactory(**control_body)

    response = self.api.get(all_models.Control, control.id)
    self.assert200(response)


# pylint: disable=too-many-public-methods
@ddt.ddt
class TestSyncServiceControl(TestCase):
  # pylint: disable=invalid-name

  """Tests for control model using sync service."""

  def setUp(self):
    """setUp, nothing else to add."""
    super(TestSyncServiceControl, self).setUp()
    self.ext_api = ExternalApiClient()
    self.generator = generator.ObjectGenerator()
    self.app_user_email = "external_app@example.com"
    self.ext_user_email = "external@example.com"
    self.ext_owner_email = "owner@example.com"
    self.ext_compliance_email = "compliance@example.com"

    self.ext_api.user_headers = {
        'X-external-user': '{"email": "%s"}' % self.ext_user_email
    }

  @staticmethod
  def prepare_control_request_body():
    """Create payload for control creation."""
    return {
        "id": 123,
        "title": "new_control",
        "context": None,
        "created_at": "2018-01-01",
        "updated_at": "2018-02-01",
        "slug": "CONTROL-01",
        "external_id": factories.SynchronizableExternalId.next(),
        "external_slug": factories.random_str(),
        "kind": "test kind",
        "means": "test means",
        "verify_frequency": "test frequency",
        "assertions": '["test assertion"]',
        "categories": '["test category"]',
        "review_status": all_models.Review.STATES.UNREVIEWED,
        "review_status_display_name": "some status",
        "due_date": "2018-03-01",
        "created_by": {
            "email": "creator@example.com",
            "name": "External Creator",
        },
        "last_submitted_at": "2018-04-01",
        "last_submitted_by": {
            "email": "owner@example.com",
            "name": "External Owner",
        },
        "last_verified_at": "2018-05-01",
        "last_verified_by": {
            "email": "compliance@example.com",
            "name": "External Compliance",
        }
    }

  def normalize_field(self, field):
    """Convert field from date/db.Model/query to string value."""
    # pylint: disable=protected-access
    normalized_field = field

    if isinstance(normalized_field, datetime):
      normalized_field = self.normalize_field(normalized_field.date())
    elif isinstance(normalized_field, date):
      normalized_field = str(normalized_field)
    elif isinstance(normalized_field, db.Model):
      normalized_field = {
          "type": normalized_field.type,
          "id": normalized_field.id
      }
    elif isinstance(normalized_field, dict) and "email" in normalized_field:
      user = user_generator.find_user_by_email(normalized_field["email"])
      normalized_field = self.normalize_field(user)
    elif isinstance(normalized_field, dict):
      normalized_field.pop("context_id", None)
      normalized_field.pop("href", None)
    elif isinstance(normalized_field, list):
      normalized_field = [self.normalize_field(i) for i in normalized_field]
    elif isinstance(
        normalized_field,
        (associationproxy._AssociationList, collections.InstrumentedList)
    ):
      normalized_field = [
          {"type": i.type, "id": i.id} for i in normalized_field
      ]
    return normalized_field

  def assert_response_fields(self, response_json, expected_body):
    """Check if data in response is the same with expected."""
    for field, value in expected_body.items():
      response_field = self.normalize_field(response_json[field])
      expected_value = self.normalize_field(value)

      self.assertEqual(
          response_field,
          expected_value,
          "Fields '{}' are not equal".format(field)
      )

  def assert_object_fields(self, object_, expected_body):
    """Check if object field values are the same with expected."""
    for field, value in expected_body.items():
      obj_value = self.normalize_field(getattr(object_, field))
      expected_value = self.normalize_field(value)
      self.assertEqual(
          obj_value,
          expected_value,
          "Fields '{}' are not equal".format(field)
      )

  @mock.patch("ggrc.settings.INTEGRATION_SERVICE_URL", "mock")
  def test_control_create(self):
    """Test control creation using sync service."""
    control_body = self.prepare_control_request_body()

    response = self.ext_api.post(all_models.Control, data={
        "control": control_body
    })

    self.assertEqual(response.status_code, 201)

    id_ = response.json.get("control").get("id")
    self.assertEqual(control_body["id"], id_)

    control = db.session.query(all_models.Control).get(id_)
    app_user = db.session.query(all_models.Person).filter(
        all_models.Person.email == self.app_user_email).one()
    ext_user = db.session.query(all_models.Person).filter(
        all_models.Person.email == self.ext_user_email).one()
    ext_owner_user = db.session.query(all_models.Person).filter(
        all_models.Person.email == self.ext_owner_email).one()
    ext_compliance_user = db.session.query(all_models.Person).filter(
        all_models.Person.email == self.ext_compliance_email).one()

    self.assertEqual(ext_user.modified_by_id, app_user.id)
    self.assertEqual(control.modified_by_id, ext_user.id)

    self.assertEqual(control.last_submitted_by_id, ext_owner_user.id)
    self.assertEqual(control.last_verified_by_id, ext_compliance_user.id)

    expected_assertions = control_body.pop("assertions")
    expected_categories = control_body.pop("categories")
    self.assertEqual(
        response.json["control"].get("assertions"),
        json.loads(expected_assertions)
    )
    self.assertEqual(
        response.json["control"].get("categories"),
        json.loads(expected_categories)
    )
    self.assert_response_fields(response.json.get("control"), control_body)
    self.assert_object_fields(control, control_body)
    self.assertEqual(control.assertions, expected_assertions)
    self.assertEqual(control.categories, expected_categories)

    revision = db.session.query(all_models.Revision).filter(
        all_models.Revision.resource_type == "Control",
        all_models.Revision.resource_id == control.id,
        all_models.Revision.action == "created",
        all_models.Revision.created_at == control.updated_at,
        all_models.Revision.updated_at == control.updated_at,
        all_models.Revision.modified_by_id == control.modified_by_id,
    ).one()
    self.assertIsNotNone(revision)

  @mock.patch("ggrc.settings.INTEGRATION_SERVICE_URL", "mock")
  def test_control_update(self):
    """Test control update using sync service."""
    external_user = factories.PersonFactory(email=self.ext_user_email)
    control = factories.ControlFactory(modified_by=external_user)

    control_body = {
        "title": "updated_title",
        "created_at": "2018-01-04",
        "updated_at": "2018-01-05",
        "kind": "test kind",
        "means": "test means",
        "verify_frequency": "test frequency",
        "assertions": '["test assertions"]',
        "categories": '["test categories"]',
    }
    response = self.ext_api.put(
        control,
        control.id,
        data=control_body
    )

    expected_assertions = control_body.pop("assertions")
    expected_categories = control_body.pop("categories")
    self.assertEqual(
        response.json["control"].get("assertions"),
        json.loads(expected_assertions)
    )
    self.assertEqual(
        response.json["control"].get("categories"),
        json.loads(expected_categories)
    )
    self.assert_response_fields(response.json["control"], control_body)

    control = all_models.Control.query.get(control.id)
    self.assert_object_fields(control, control_body)
    self.assertEqual(control.assertions, expected_assertions)
    self.assertEqual(control.categories, expected_categories)

    revision = db.session.query(all_models.Revision).filter(
        all_models.Revision.resource_type == "Control",
        all_models.Revision.resource_id == control.id,
        all_models.Revision.action == "modified",
        all_models.Revision.created_at == control.updated_at,
        all_models.Revision.updated_at == control.updated_at,
        all_models.Revision.modified_by_id == control.modified_by_id,
    ).one()
    self.assertIsNotNone(revision)

  @ddt.data((" http://www.some.url", " http://www.some.url"),
            ("<a>http://www.some.url</a>",
             "<a>http://www.some.url</a>"))
  @ddt.unpack
  def test_control_rich_text_validate(self, initial_value, expected_value):
    """Test rich text validation for control."""
    response = self.ext_api.post(all_models.Control, data={
        "control": {
            "id": 11111,
            "title": "Some title",
            "context": None,
            "external_id": factories.SynchronizableExternalId.next(),
            "external_slug": factories.random_str(),
            "assertions": '["any assertion"]',
            "review_status": all_models.Review.STATES.UNREVIEWED,
            "review_status_display_name": "any status",
        },
    })
    self.assertEqual(response.status_code, 201)
    control = all_models.Control.query.filter_by(title="Some title").first()

    cad = factories.CustomAttributeDefinitionFactory(
        definition_type="control",
        definition_id=control.id,
        attribute_type="Rich Text",
        title="CA",
    )

    response = self.ext_api.post(all_models.CustomAttributeValue, data={
        "custom_attribute_value": {
            "custom_attribute_id": cad.id,
            "attributable_type": "control",
            "attributable_id": control.id,
            "attribute_value": initial_value,
            "context": {"id": None},
        }
    })
    self.assertEqual(response.status_code, 201)

    control = all_models.Control.query.filter_by(title="Some title").first()
    self.assertEqual(control.custom_attribute_values[0].attribute_value,
                     expected_value)

  def test_create_with_assertions(self):
    """Check control creation with assertions pass"""
    response = self.ext_api.post(all_models.Control, data={
        "control": {
            "title": "Control title",
            "context": None,
            "recipients": "Admin,Control Operators,Control Owners",
            "send_by_default": 0,
            "external_id": factories.SynchronizableExternalId.next(),
            "external_slug": factories.random_str(),
            "assertions": '["test assertion"]',
            "review_status": all_models.Review.STATES.UNREVIEWED,
            "review_status_display_name": "some status",
        }
    })

    self.assertEqual(response.status_code, 201)
    control = all_models.Control.query.first()
    self.assertIsNotNone(control)
    self.assertEqual('["test assertion"]', control.assertions)

  def test_has_test_plan(self):
    """Check test plan setup to control."""
    control = factories.ControlFactory(test_plan="This is a test text")
    control = db.session.query(all_models.Control).get(control.id)
    self.assertEqual(control.test_plan, "This is a test text")

  def test_set_end_date(self):
    """External app can update end_date attribute"""
    control = factories.ControlFactory()
    resp = self.ext_api.put(
        control, control.id, data={"end_date": "2015-10-10"}
    )
    self.assertStatus(resp, 200)
    control = db.session.query(all_models.Control).get(control.id)
    self.assertIsNone(control.end_date)

  def test_set_deprecated_status(self):
    """Deprecated status setup end_date."""
    control = factories.ControlFactory()
    self.assertIsNone(control.end_date)
    self.ext_api.put(control, control.id,
                     data={"status": all_models.Control.DEPRECATED})
    control = db.session.query(all_models.Control).get(control.id)
    self.assertIsNotNone(control.end_date)

  def test_create_comments(self):
    """Test external comments creation for control."""
    response = self.ext_api.post(all_models.Control, data={
        "control": {
            "id": 123,
            "title": "Control title",
            "context": None,
            "external_id": factories.SynchronizableExternalId.next(),
            "external_slug": factories.random_str(),
            "assertions": '["test assertion"]',
            "review_status": all_models.Review.STATES.UNREVIEWED,
            "review_status_display_name": "some status",
        },
    })
    self.assertEqual(response.status_code, 201)

    response = self.ext_api.post(all_models.ExternalComment, data={
        "external_comment": {
            "id": 1,
            "external_id": 1,
            "external_slug": factories.random_str(),
            "description": "test comment",
            "context": None
        }
    })
    self.assertEqual(response.status_code, 201)
    comments = db.session.query(all_models.ExternalComment.description).all()
    self.assertEqual(comments, [("test comment",)])

    response = self.ext_api.post(all_models.Relationship, data={
        "relationship": {
            "source": {"id": 123, "type": "Control"},
            "destination": {"id": 1, "type": "ExternalComment"},
            "context": None,
            "is_external": True
        },
    })
    self.assertEqual(response.status_code, 201)
    rels = all_models.Relationship.query.filter_by(
        source_type="Control",
        source_id=123,
        destination_type="ExternalComment",
        destination_id=1
    )
    self.assertEqual(rels.count(), 1)

  def test_query_external_comment(self):
    """Test query endpoint for ExternalComments collection."""
    with factories.single_commit():
      control = factories.ControlFactory()
      comment = factories.ExternalCommentFactory(description="test comment")
      factories.RelationshipFactory(source=control, destination=comment)

    request_data = [{
        "filters": {
            "expression": {
                "object_name": "Control",
                "op": {
                    "name": "relevant"
                },
                "ids": [control.id]
            },
        },
        "object_name":"ExternalComment",
        "order_by": [{"name": "created_at", "desc": "true"}]
    }]
    response = self.ext_api.post(
        url="/query",
        data=request_data,
    )
    self.assert200(response)
    response_data = response.json[0]["ExternalComment"]
    self.assertEqual(response_data["count"], 1)
    self.assertEqual(response_data["values"][0]["description"], "test comment")

  @ddt.data("created_at", "description")
  def test_external_comments_order(self, order_by_attr):
    """Test order of ExternalComments returned by /query."""
    with factories.single_commit():
      control = factories.ControlFactory()
      for _ in range(5):
        comment = factories.ExternalCommentFactory(
            description=factories.random_str()
        )
        factories.RelationshipFactory(source=control, destination=comment)

    request_data = [{
        "filters": {
            "expression": {
                "object_name": "Control",
                "op": {
                    "name": "relevant"
                },
                "ids": [control.id]
            },
        },
        "object_name":"ExternalComment",
        "order_by": [{"name": order_by_attr, "desc": "true"}]
    }]
    response = self.ext_api.post(
        data=request_data,
        url="/query"
    )
    self.assert200(response)
    response_data = response.json[0]["ExternalComment"]
    comments = [val["description"] for val in response_data["values"]]
    expected_comments = db.session.query(
        all_models.ExternalComment.description
    ).order_by(
        getattr(all_models.ExternalComment, order_by_attr).desc()
    )
    self.assertEqual(comments, [i[0] for i in expected_comments])

  def test_create_without_external_id(self):
    """Check control creation without external_id"""

    request = self.prepare_control_request_body()
    del request['external_id']
    response = self.ext_api.post(all_models.Control, data=request)

    self.assert400(response)

  def test_create_with_empty_external_id(self):
    """Check control creation with empty external_id"""

    request = self.prepare_control_request_body()
    request['external_id'] = None
    response = self.ext_api.post(all_models.Control, data=request)

    self.assert400(response)

  def test_create_unique_external_id(self):
    """Check control creation with non-unique external_id"""

    request1 = self.prepare_control_request_body()
    response1 = self.ext_api.post(
        all_models.Control, data={'control': request1}
    )
    prev_external_id = response1.json['control']['external_id']

    request2 = self.prepare_control_request_body()
    request2['external_id'] = prev_external_id
    response2 = self.ext_api.post(
        all_models.Control, data={'control': request2}
    )

    self.assert400(response2)

  def test_update_external_id_to_null(self):
    """Test external_id is not set to None"""
    control = factories.ControlFactory()
    response = self.ext_api.put(
        control, control.id, data={"external_id": None}
    )
    self.assert400(response)
    self.assertEqual(response.json["message"],
                     "External ID for the object is not specified")

    control = db.session.query(all_models.Control).get(control.id)
    self.assertIsNotNone(control.external_id)

  def test_update_external_id(self):
    """Test external_id is updated"""
    control = factories.ControlFactory()
    new_value = factories.SynchronizableExternalId.next()
    self.ext_api.put(control, control.id, data={"external_id": new_value})

    control = db.session.query(all_models.Control).get(control.id)
    self.assertEquals(control.external_id, new_value)

  def test_create_without_review_status(self):
    """Check control creation without review_status"""

    request = self.prepare_control_request_body()
    del request['review_status']
    response = self.ext_api.post(all_models.Control, data=request)
    self.assert400(response)

  def test_create_with_empty_review_status(self):
    """Check control creation with empty review_status"""

    request = self.prepare_control_request_body()
    request['review_status'] = None
    response = self.ext_api.post(all_models.Control, data=request)

    self.assert400(response)

  def test_update_review_status_to_null(self):
    """Test review_status is not set to None"""
    control = factories.ControlFactory()
    response = self.ext_api.put(
        control, control.id, data={"review_status": None}
    )
    self.assert400(response)
    self.assertEqual(response.json["message"],
                     "review_status for the object is not specified")

    control = db.session.query(all_models.Control).get(control.id)
    self.assertIsNotNone(control.external_id)

  def test_update_review_status(self):
    """Test review_status is updated"""
    control = factories.ControlFactory()
    new_value = all_models.Review.STATES.REVIEWED
    self.ext_api.put(control, control.id, data={"review_status": new_value})

    control = db.session.query(all_models.Control).get(control.id)
    self.assertEquals(control.review_status, new_value)

  def test_create_without_review_status_display_name(self):
    """Check control creation without review_status_display_name"""

    request = self.prepare_control_request_body()
    del request['review_status_display_name']
    response = self.ext_api.post(all_models.Control, data=request)
    print response.json
    self.assert400(response)

  def test_create_with_empty_review_status_display_name(self):
    """Check control creation with empty review_status_display_name"""

    request = self.prepare_control_request_body()
    request['review_status_display_name'] = None
    response = self.ext_api.post(all_models.Control, data=request)

    self.assert400(response)

  def test_update_review_status_display_name_to_null(self):
    """Test review_status_display_name is not set to None"""
    control = factories.ControlFactory()
    response = self.ext_api.put(
        control, control.id, data={"review_status_display_name": None}
    )
    self.assert400(response)
    self.assertEqual(response.json["message"],
                     "review_status_display_name for the object "
                     "is not specified")

    control = db.session.query(all_models.Control).get(control.id)
    self.assertIsNotNone(control.external_id)

  def test_update_review_status_display_name(self):
    """Test review_status_display_name is updated"""
    control = factories.ControlFactory()
    new_value = "value12345"
    self.ext_api.put(
        control, control.id, data={"review_status_display_name": new_value}
    )

    control = db.session.query(all_models.Control).get(control.id)
    self.assertEquals(control.review_status_display_name, new_value)

  @ddt.data(
      ("kind", ["1", "2", "3"], "2"),
      ("means", ["1", "1", "1"], "1"),
      ("verify_frequency", ["3", "2", "3"], "3"),
  )
  @ddt.unpack
  def test_control_query_string(self, field, possible_values, search_value):
    """Test querying '{0}' field for control."""
    with factories.single_commit():
      for val in possible_values:
        factories.ControlFactory(**{field: val})

    request_data = [{
        'fields': [],
        'filters': {
            'expression': {
                'left': field,
                'op': {'name': '='},
                'right': search_value,
            },
        },
        'object_name': 'Control',
        'type': 'values',
    }]
    response = self.ext_api.post(
        data=request_data,
        url="/query"
    )
    self.assert200(response)
    response_data = response.json[0]["Control"]

    expected_controls = all_models.Control.query.filter_by(
        **{field: search_value}
    )
    self.assertEqual(expected_controls.count(), response_data.get("count"))

    expected_values = [getattr(i, field) for i in expected_controls]
    actual_values = [val.get(field) for val in response_data.get("values")]
    self.assertEqual(expected_values, actual_values)

  @ddt.data(
      ("assertions", ['["a", "b", "c"]', '["1", "2", "3"]'], "c"),
      ("categories", ['["a"]', '["1", "2", "3"]'], "1"),
      ("assertions", ['["a", "b"]', '["1", "2"]'], "3"),
  )
  @ddt.unpack
  def test_control_query_json(self, field, possible_values, search_value):
    """Test querying '{0}' field for control."""
    with factories.single_commit():
      for val in possible_values:
        factories.ControlFactory(**{field: val})

    request_data = [{
        "fields": [],
        "object_name": "Control",
        "type": "values",
        "filters": {
            "expression": {
                "left": field,
                "op": {"name": "="},
                "right": search_value,
            },
        },
    }]
    response = self.ext_api.post(
        data=request_data,
        url="/query"
    )
    self.assert200(response)
    response_data = response.json[0]["Control"]

    model_field = getattr(all_models.Control, field)
    expected_controls = all_models.Control.query.filter(
        model_field.like("%{}%".format(search_value))
    )
    self.assertEqual(expected_controls.count(), response_data.get("count"))

    expected_values = [
        json.loads(getattr(i, field)) for i in expected_controls
    ]
    actual_values = [val.get(field) for val in response_data.get("values")]
    self.assertEqual(expected_values, actual_values)

  @ddt.data(
      ("kind", factories.random_str()),
      ("means", factories.random_str()),
      ("verify_frequency", factories.random_str()),
      ("assertions", ["assertion1", "assertion2"]),
      ("assertions", []),
      ("categories", ["c1", "c2", "c3"]),
      ("categories", []),
  )
  @ddt.unpack
  def test_new_revision(self, field, value):
    """Test if content of new revision is correct for Control '{0}' field."""
    control = factories.ControlFactory(**{field: value})

    response = self.ext_api.get(
        url="/api/revisions"
        "?resource_type={}&resource_id={}".format(control.type, control.id)
    )
    self.assert200(response)
    revisions = response.json["revisions_collection"]["revisions"]
    self.assertEqual(len(revisions), 1)
    self.assertEqual(revisions[0].get("content", {}).get(field), value)

  @ddt.data("kind", "means", "verify_frequency")
  def test_old_option_revision(self, field):
    """Test if old revision content is correct for Control '{0}' field."""
    field_value = factories.random_str()
    control = factories.ControlFactory(**{field: field_value})
    control_revision = all_models.Revision.query.filter_by(
        resource_type=control.type,
        resource_id=control.id
    ).one()
    revision_content = control_revision.content
    revision_content[field] = {
        "id": "123",
        "title": "some title",
        "type": "Option",
    }
    control_revision.content = revision_content
    db.session.commit()

    response = self.ext_api.get(
        url="/api/revisions"
        "?resource_type={}&resource_id={}".format(control.type, control.id)
    )
    self.assert200(response)
    revisions = response.json["revisions_collection"]["revisions"]
    self.assertEqual(len(revisions), 1)
    self.assertEqual(revisions[0].get("content", {}).get(field), "some title")

  @ddt.data(
      (
          "assertions",
          [
              {
                  "name": "Availability",
                  "type": "ControlAssertion",
                  "id": 39,
              },
              {
                  "name": "Security",
                  "type": "ControlAssertion",
                  "id": 40,
              },
          ],
          ["Availability", "Security"]
      ),
      (
          "categories",
          [
              {
                  "name": "Authentication",
                  "type": "ControlCategory",
                  "id": 49,
              },
              {
                  "name": "Monitoring",
                  "type": "ControlCategory",
                  "id": 55,
              },
          ],
          ["Authentication", "Monitoring"]
      ),
  )
  @ddt.unpack
  def test_old_category_revision(self, field, new_value, expected):
    """Test if old revision content is correct for Control '{0}' field."""
    control = factories.ControlFactory()
    control_revision = all_models.Revision.query.filter_by(
        resource_type=control.type,
        resource_id=control.id
    ).one()
    revision_content = control_revision.content
    revision_content[field] = new_value
    control_revision.content = revision_content
    db.session.commit()

    response = self.ext_api.get(
        url="/api/revisions"
        "?resource_type={}&resource_id={}".format(control.type, control.id)
    )
    self.assert200(response)
    revisions = response.json["revisions_collection"]["revisions"]
    self.assertEqual(len(revisions), 1)
    self.assertEqual(revisions[0].get("content", {}).get(field), expected)

  @staticmethod
  def setup_people(access_control_list):
    """Create Person objects specified in access_control_list."""
    all_users = set()
    for users in access_control_list.values():
      all_users.update({(user["email"], user["name"]) for user in users})

    with factories.single_commit():
      for email, name in all_users:
        factories.PersonFactory(email=email, name=name)

  def assert_obj_acl(self, obj, access_control_list):
    """Validate correctness of object access_control_list.

    Args:
        obj: Object for which acl should be checked.
        access_control_list: Dict of format
          {<role name>:[{"name": <user name>, "email": <user email>}.
    """
    actual_acl = {
        (a.acl_item.ac_role.name, a.person.email)
        for a in obj.access_control_list
    }
    expected_acl = {
        (role, person["email"])
        for role, people in access_control_list.items()
        for person in people
    }
    self.assertEqual(actual_acl, expected_acl)

  @mock.patch("ggrc.settings.INTEGRATION_SERVICE_URL", "mock")
  @ddt.data(
      {
          "Admin": {
              "email": "user1@example.com",
              "name": "user1",
          },
      },
      {
          "Admin": "user1@example.com",
      },
  )
  def test_invalid_acl_format(self, access_control_list):
    """Test creation of new object with acl in invalid format."""
    response = self.ext_api.post(all_models.Control, data={
        "control": {
            "id": 123,
            "external_id": factories.SynchronizableExternalId.next(),
            "external_slug": factories.random_str(),
            "title": "new_control",
            "context": None,
            "access_control_list": access_control_list,
            "assertions": '["test assertion"]',
            "review_status": all_models.Review.STATES.UNREVIEWED,
            "review_status_display_name": "some status",
        }
    })
    self.assert400(response)
    expected_err = synchronizable.RoleableSynchronizable.INVALID_ACL_ERROR
    self.assertEqual(response.json, expected_err)
    control = all_models.Control.query.filter_by(id=123)
    self.assertEqual(control.count(), 0)

  def test_control_with_tg_update(self):
    """Test updating of Control mapped to TaskGroup."""
    with factories.single_commit():
      control = factories.ControlFactory()
      control_id = control.id
      task_group = wf_factories.TaskGroupFactory()
      factories.RelationshipFactory(
          source=task_group,
          destination=control
      )

    response = self.ext_api.put(control, control_id, data={
        "title": "new title",
        "task_groups": [],
    })
    self.assert200(response)
    control = all_models.Control.query.get(control_id)
    self.assertEqual(control.title, "new title")
    tg_ids = [id_[0] for id_ in db.session.query(all_models.TaskGroup.id)]
    self.assertEqual(len(tg_ids), 1)
    self.assertEqual([tg.source_id for tg in control.related_sources], tg_ids)
    tg_mapped_obj_ids = [
        id_[0] for id_ in db.session.query(
            all_models.Relationship.destination_id
        ).filter(
            all_models.Relationship.source_type == 'TaskGroup',
            all_models.Relationship.source_id.in_(tg_ids),
        )
    ]
    self.assertEqual(len(tg_mapped_obj_ids), 1)

  @staticmethod
  def generate_minimal_control_body():
    """Generate minimal control body"""
    return {
        "title": factories.random_str(),
        "external_id": factories.SynchronizableExternalId.next(),
        "external_slug": factories.random_str(),
        "context": None,
        "review_status": all_models.Review.STATES.UNREVIEWED,
        "review_status_display_name": "some status",
    }

  def test_control_with_duplicated_title(self):
    """Test control with duplicated title."""
    control_1 = self.generate_minimal_control_body()
    response = self.ext_api.post(all_models.Control, data={
        "control": control_1
    })
    self.assertEqual(response.status_code, 201)

    control_2 = self.generate_minimal_control_body()
    control_2["title"] = control_1["title"]
    response = self.ext_api.post(all_models.Control, data={
        "control": control_2
    })
    self.assertEqual(response.status_code, 201)

  def test_external_comment_acl(self):
    """Test automatic assigning current user to ExternalComment Admin."""
    response = self.ext_api.post(all_models.ExternalComment, data={
        "external_comment": {
            "id": 1,
            "external_id": 1,
            "external_slug": factories.random_str(),
            "description": "test comment",
            "context": None,
            "access_control_list": {
                "Admin": [
                    {
                        "email": "user1@example.com",
                        "name": "user1",
                    },
                ],
            },
        }
    })
    self.assertEqual(response.status_code, 201)
    comment = all_models.ExternalComment.query.get(1)
    comment_admin = comment.get_persons_for_rolename("Admin")
    self.assertEqual(
        [i.email for i in comment_admin],
        ["user1@example.com"]
    )

  @mock.patch("ggrc.settings.INTEGRATION_SERVICE_URL", "mock")
  @ddt.data(
      {
          "Admin": [
              {
                  "email": "user1@example.com",
                  "name": "user1",
              },
          ],
      },
      {
          "Admin": [
              {
                  "email": "user1@example.com",
                  "name": "user1",
              },
              {
                  "email": "user2@example.com",
                  "name": "user2",
              },
          ],
          "Principal Assignees": [
              {
                  "email": "user2@example.com",
                  "name": "user2",
              },
              {
                  "email": "user3@example.com",
                  "name": "user3",
              },
          ]
      },
      {}
  )
  def test_control_acl_create(self, access_control_list):
    """Test creation of control with non empty acl."""
    self.setup_people(access_control_list)

    response = self.ext_api.post(all_models.Control, data={
        "control": {
            "id": 123,
            "title": "new_control",
            "context": None,
            "access_control_list": access_control_list,
            "assertions": '["test assertion"]',
            "review_status": "Unreviewed",
            "external_id": "123",
            "external_slug": "Control-123",
            "review_status_display_name": "some name",
        }
    })

    self.assertEqual(201, response.status_code)

    control = all_models.Control.query.get(123)
    self.assert_obj_acl(control, access_control_list)

  def test_acl_new_people_create(self):
    """Test creation of control with acl which contain new people."""
    access_control_list = {
        "Admin": [
            {
                "email": "user1@example.com",
                "name": "user1",
            },
            {
                "email": "user2@example.com",
                "name": "user2",
            },
        ]
    }
    response = self.ext_api.post(all_models.Control, data={
        "control": {
            "id": 123,
            "title": "new_control",
            "context": None,
            "access_control_list": access_control_list,
            "assertions": '["test assertion"]',
            "review_status": "Unreviewed",
            "external_id": "123",
            "external_slug": "Control-123",
            "review_status_display_name": "some name",
        }
    })
    self.assertEqual(201, response.status_code)

    for expected_person in access_control_list["Admin"]:
      user = all_models.Person.query.filter_by(
          email=expected_person["email"]
      ).one()
      self.assertEqual(user.name, expected_person["name"])
      self.assertEqual([ur.role.name for ur in user.user_roles], ["Creator"])

    control = all_models.Control.query.get(123)
    self.assert_obj_acl(control, access_control_list)

  def test_control_acl_update(self):
    """Test updating of control with non empty acl."""
    with factories.single_commit():
      control = factories.ControlFactory()
      person = factories.PersonFactory()
      control.add_person_with_role_name(person, "Admin")

    access_control_list = {
        "Admin": [
            {
                "email": "user1@example.com",
                "name": "user1",
            },
            {
                "email": "user2@example.com",
                "name": "user2",
            },
        ]
    }
    self.setup_people(access_control_list)

    response = self.ext_api.put(control, control.id, data={
        "access_control_list": access_control_list,
    })
    self.assert200(response)
    control = all_models.Control.query.get(control.id)
    self.assert_obj_acl(control, access_control_list)

  def test_acl_new_people_update(self):
    """Test updating of control with acl which contain new people."""
    person = self.generator.generate_person(user_role="Creator")[1]
    with factories.single_commit():
      control = factories.ControlFactory()
      control.add_person_with_role_name(person, "Admin")

    access_control_list = {
        "Admin": [
            {
                "email": person.email,
                "name": person.name,
            }
        ],
        "Principal Assignees": [
            {
                "email": person.email,
                "name": person.name,
            },
            {
                "email": "user2@example.com",
                "name": "user2",
            },
            {
                "email": "user3@example.com",
                "name": "user3",
            },
        ]
    }
    response = self.ext_api.put(control, control.id, data={
        "access_control_list": access_control_list,
    })
    self.assert200(response)

    for expected_person in access_control_list["Admin"]:
      user = all_models.Person.query.filter_by(
          email=expected_person["email"]
      ).one()
      self.assertEqual(user.name, expected_person["name"])
      self.assertEqual([ur.role.name for ur in user.user_roles], ["Creator"])

    control = all_models.Control.query.get(control.id)
    self.assert_obj_acl(control, access_control_list)

  def test_wrong_role_acl_update(self):
    """Test updating of control with non empty acl."""
    with factories.single_commit():
      control = factories.ControlFactory()
      person = factories.PersonFactory(name="user1", email="user1@example.com")
      control.add_person_with_role_name(person, "Admin")

    access_control_list = {
        "Non-existing role": [
            {
                "email": "user2@example.com",
                "name": "user2",
            },
        ]
    }

    response = self.ext_api.put(control, control.id, data={
        "access_control_list": access_control_list,
    })
    self.assert400(response)
    self.assertEqual(
        response.json["message"],
        "Role 'Non-existing role' does not exist"
    )
    control = all_models.Control.query.get(control.id)
    self.assert_obj_acl(
        control,
        {"Admin": [{"name": "user1", "email": "user1@example.com"}]}
    )

  @mock.patch("ggrc.settings.INTEGRATION_SERVICE_URL", new="mock")
  def test_cad_create(self):
    self.ext_api.user_headers = {
        'X-external-user': json.dumps(
            {'email': "test_test@test.com", 'user': "Vasya"}
        )
    }
    response = self.ext_api.post(all_models.CustomAttributeDefinition, data={
        "custom_attribute_definition": {
            "attribute_type": "Rich Text",
            "title": "Rich Text Attribute",
            "definition_type": "control",
            "context": {"id": None},
        }
    })
    self.assertStatus(response, 201)
    cad = all_models.CustomAttributeDefinition.query.filter_by(
        title="Rich Text Attribute"
    ).one()
    self.assertIsNotNone(cad)
