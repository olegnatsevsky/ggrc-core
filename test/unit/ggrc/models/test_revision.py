# Copyright (C) 2018 Google Inc.

# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Unittests for Revision model """

import datetime
import unittest

import ddt
import mock

from ggrc.models import all_models


@ddt.ddt
class TestCheckPopulatedContent(unittest.TestCase):
  """Unittest checks populated content."""
  # pylint: disable=invalid-name

  LIST_OF_REQUIRED_ROLES = [
      "Principal Assignees",
      "Secondary Assignees",
      "Primary Contacts",
      "Secondary Contacts",
  ]

  def setUp(self):
    super(TestCheckPopulatedContent, self).setUp()
    self.object_type = "Control"
    self.object_id = 1
    self.user_id = 123

  @ddt.data(
      # content, expected
      (None, None),
      ('principal_assessor', ("Principal Assignees", 1)),
      ('secondary_assessor', ("Secondary Assignees", 2)),
      ('contact', ("Primary Contacts", 3)),
      ('secondary_contact', ("Secondary Contacts", 4)),
      ('owners', ("Admin", 5)),
  )
  @ddt.unpack
  def test_check_populated_content(self, key, role):
    """Test populated content for revision if ACL doesn't exists."""
    content = {}
    if key:
      content[key] = {"id": self.user_id}
    expected = {"access_control_list": []}
    role_dict = {}
    if role:
      role_name, role_id = role
      expected["access_control_list"].append({
          "display_name": role_name,
          "ac_role_id": role_id,
          "context_id": None,
          "created_at": None,
          "object_type": self.object_type,
          "updated_at": None,
          "object_id": self.object_id,
          "modified_by_id": None,
          "person_id": self.user_id,
          # Frontend require data in such format
          "person": {
              "id": self.user_id,
              "type": "Person",
              "href": "/api/people/{}".format(self.user_id)
          },
          "modified_by": None,
          "id": None,
      })
      role_dict[role_id] = role_name
    obj = mock.Mock()
    obj.id = self.object_id
    obj.__class__.__name__ = self.object_type
    revision = all_models.Revision(obj, mock.Mock(), mock.Mock(), content)

    with mock.patch("ggrc.access_control.role.get_custom_roles_for",
                    return_value=role_dict) as get_roles:
      self.assertEqual(revision.populate_acl(), expected)
      get_roles.assert_called_once_with(self.object_type)

  @ddt.data(None, {}, {"id": None})
  def test_populated_content_no_user(self, user_dict):
    """Test populated content for revision without user id."""
    content = {"principal_assessor": user_dict}
    role_dict = {1: "Principal Assignees"}
    expected = {"access_control_list": []}
    obj = mock.Mock()
    obj.id = self.object_id
    obj.__class__.__name__ = self.object_type
    revision = all_models.Revision(obj, mock.Mock(), mock.Mock(), content)
    with mock.patch("ggrc.access_control.role.get_custom_roles_for",
                    return_value=role_dict) as get_roles:
      self.assertEqual(revision.populate_acl(), expected)
      get_roles.assert_called_once_with(self.object_type)

  @ddt.data(
      'principal_assessor',
      'secondary_assessor',
      'contact',
      'secondary_contact',
  )
  def test_populated_content_no_role(self, key):
    """Test populated content for revision without roles."""
    content = {key: {"id": self.user_id}}
    expected = {"access_control_list": []}
    obj = mock.Mock()
    obj.id = self.object_id
    obj.__class__.__name__ = self.object_type
    revision = all_models.Revision(obj, mock.Mock(), mock.Mock(), content)
    with mock.patch("ggrc.access_control.role.get_custom_roles_for",
                    return_value={}) as get_roles:
      self.assertEqual(revision.populate_acl(), expected)
      get_roles.assert_called_once_with(self.object_type)

  @ddt.data({
      "url": "www.url-foo.com",
      "reference_url": "www.refurl-bar.com",
      "created_at": "2017-07-15T15:49:14",
      "updated_at": "2017-08-20T13:32:42",
  }, {
      "url": "www.url-foo.com",
      "reference_url": "www.refurl-bar.com",
  })
  def test_populated_content_urls(self, content):
    """Test populated content for revision with urls."""
    dates_in_content = "created_at" in content

    if dates_in_content:
      expected_created_at = "2017-07-15T15:49:14"
      expected_updated_at = "2017-08-20T13:32:42"
    else:
      # Revision's own dates should be used as a fallback
      expected_created_at = "2017-11-12T13:14:15"
      expected_updated_at = "2018-11-12T13:14:15"

    expected = [{'display_name': 'www.url-foo.com',
                 'document_type': 'REFERENCE_URL',
                 'id': None,
                 'link': 'www.url-foo.com',
                 'title': 'www.url-foo.com',
                 'created_at': expected_created_at,
                 'updated_at': expected_updated_at, },
                {'display_name': 'www.refurl-bar.com',
                 'document_type': 'REFERENCE_URL',
                 'id': None,
                 'link': 'www.refurl-bar.com',
                 'title': 'www.refurl-bar.com',
                 'created_at': expected_created_at,
                 'updated_at': expected_updated_at, }]

    obj = mock.Mock()
    obj.id = self.object_id
    obj.__class__.__name__ = self.object_type
    revision = all_models.Revision(obj, mock.Mock(), mock.Mock(), content)
    revision.created_at = datetime.datetime(2017, 11, 12, 13, 14, 15)
    revision.updated_at = datetime.datetime(2018, 11, 12, 13, 14, 15)

    with mock.patch("ggrc.access_control.role.get_custom_roles_for",
                    return_value={}):
      self.assertEqual(revision.populate_reference_url()["reference_url"],
                       expected)

  @ddt.data([{"label": "label"}, [{"id": None, "name": "label"}]],
            [{"label": ""}, []],
            [{"label": None}, []])
  @ddt.unpack
  def test_populated_content_labels(self, content, expected):
    """Test populated content for old revision with label."""
    obj = mock.Mock()
    obj.id = self.object_id
    obj.__class__.__name__ = self.object_type

    revision = all_models.Revision(obj, mock.Mock(), mock.Mock(), content)

    with mock.patch("ggrc.access_control.role.get_custom_roles_for",
                    return_value={},):
      self.assertEqual(revision.populate_labels()["labels"],
                       expected)

  @ddt.data([{"status": "Active"}, {"status": "Active"}, "AccessGroup"],
            [{"status": "Deprecated"}, {"status": "Deprecated"}, "Clause"],
            [{"status": "Draft"}, {"status": "Draft"}, "Control"],
            [{"status": "Effective"}, {"status": "Active"}, "DataAsset"],
            [{"status": "Final"}, {"status": "Active"}, "Directive"],
            [{"status": "In Scope"}, {"status": "Active"}, "Facility"],
            [{"status": "Ineffective"}, {"status": "Active"}, "Issue"],
            [{"status": "Launched"}, {"status": "Active"}, "Market"],
            [{"status": "Not in Scope"}, {"status": "Draft"}, "Objective"],
            [{"status": "Not Launched"}, {"status": "Draft"}, "OrgGroup"],
            [{"status": "Not Launched"}, {"status": "Draft"}, "Product"],
            [{"status": "Not Launched"}, {"status": "Draft"}, "Program"],
            [{"status": "Not Launched"}, {"status": "Draft"}, "Project"],
            [{"status": "Not Launched"}, {"status": "Draft"}, "Section"],
            [{"status": "Not Launched"}, {"status": "Draft"}, "System"],
            [{"status": "Not Launched"}, {"status": "Draft"}, "Vendor"],
            [{"status": "Not Launched"}, {"status": "Draft"}, "Risk"],
            [{"status": "Not Launched"}, {"status": "Draft"}, "Threat"],
            [{"status": "Not Launched"}, {}, "Regulation"])
  @ddt.unpack
  def test_populated_status(self, content, expected_content, resource_type):
    """Test populated content with status '{0}' to '{1}' in Model '{2}'."""
    obj = mock.Mock()
    obj.id = self.object_id
    obj.__class__.__name__ = resource_type

    revision = all_models.Revision(obj, mock.Mock(), mock.Mock(), content)
    self.assertEqual(revision.populate_status(), expected_content)

  @ddt.data(
      ({}, {}),
      ({"document_evidence": []}, {"document_evidence": []}),
      (
          {"document_evidence": [
              {"link": u"aa", "title": u"bb", "display_name": u"bb"},
          ]},
          {"document_evidence": [
              {"link": u"aa", "title": u"bb", "display_name": u"aa bb"},
          ]}
      ),
      (
          {"document_evidence": [
              {"link": u"aa", "title": u"bb", "display_name": u"bb"},
              {"link": u"aa\u5555", "title": u"", "display_name": u""},
          ]},
          {"document_evidence": [
              {"link": u"aa", "title": u"bb", "display_name": u"aa bb"},
              {"link": u"aa\u5555", "title": u"", "display_name": u"aa\u5555"},
          ]}
      ),
  )
  @ddt.unpack
  def test_populated_content_evidence(self, content, expected_evidence):
    """Test display names for document evidence in revision content.

    The display name should contain link and title, like we used to have in
    slugs.
    """
    obj = mock.Mock()
    obj.id = self.object_id
    obj.__class__.__name__ = self.object_type

    revision = all_models.Revision(obj, mock.Mock(), mock.Mock(), content)

    self.assertEqual(
        revision._document_evidence_hack(),
        expected_evidence,
    )

  def test_populate_acl_from_gca_person_type(self):
    """Test populated ACL from old GCA Person type"""
    obj = mock.Mock()
    obj.id = self.object_id
    obj.__class__.__name__ = self.object_type
    content = {
        "custom_attribute_values": [{
            "display_name": "some_display_name",
            "attribute_object": {
                "context_id": None,
                "href": "/api/people/3",
                "type": "Person",
                "id": "3"
            },
            "custom_attribute_id": 1,
            "context_id": None,
            "created_at": "2018-01-19T14:57:40",
            "updated_at": "2018-01-19T14:57:40",
            "attributable_type": "Control",
            "modified_by": None,
            "modified_by_id": 1,
            "attribute_value": "Person",
            "type": "CustomAttributeValue",
            "id": 46,
            "attributable_id": 23
        }],

        "custom_attribute_definitions": [{
            "mandatory": None,
            "title": "map_person_gca",
            "multi_choice_options": None,
            "created_at": "2018-01-19T14:57:39",
            "modified_by_id": None,
            "updated_at": "2018-01-19T14:57:39",
            "multi_choice_mandatory": None,
            "definition_id": None,
            "definition_type": "control",
            "modified_by": None,
            "helptext": None,
            "placeholder": None,
            "attribute_type": "Map:Person",
            "context_id": None,
            "display_name": "map_person_gca",
            "type": "CustomAttributeDefinition",
            "id": 1
        }]
    }

    dummy_ac_role_id = 10
    revision = all_models.Revision(obj, mock.Mock(), mock.Mock(), content)
    with mock.patch("ggrc.access_control.role.get_custom_roles_for",
                    return_value={dummy_ac_role_id: 'map_person_gca'}):
      result = revision.populate_acl_from_migrated_gcas()

      result_ac = result['access_control_list'][0]
      self.assertEqual(len(result['access_control_list']), 1)
      self.assertEqual(len(result['custom_attribute_values']), 0)
      self.assertEqual(len(result['custom_attribute_definitions']), 0)

      cav = content['custom_attribute_values'][0]
      self.assertEqual(result_ac['display_name'], cav['display_name'])
      self.assertEqual(result_ac['ac_role_id'], dummy_ac_role_id)
      self.assertEqual(result_ac['context_id'], cav['context_id'])
      self.assertEqual(result_ac['created_at'], cav['created_at'])
      self.assertEqual(result_ac['updated_at'], cav['updated_at'])
      self.assertEqual(result_ac['object_type'], cav['attributable_type'])
      self.assertEqual(result_ac['object_id'], cav['attributable_id'])
      self.assertEqual(result_ac['parent_id'], None)
      self.assertEqual(result_ac['modified_by_id'], cav['modified_by_id'])
      self.assertEqual(result_ac['modified_by'], cav['modified_by'])
      self.assertEqual(result_ac['type'], 'AccessControlList')
      self.assertEqual(result_ac['person_id'], cav['attribute_object']['id'])
      self.assertEqual(result_ac['person']['href'],
                       cav['attribute_object']['href'])
      self.assertEqual(result_ac['person']['type'],
                       cav['attribute_object']['type'])
      self.assertEqual(result_ac['person']['id'],
                       cav['attribute_object']['id'])

  def test_populate_acl_from_gca_text_type(self):
    """Test populated ACL from old GCA not person type should stay unchanged"""
    obj = mock.Mock()
    obj.id = self.object_id
    obj.__class__.__name__ = self.object_type
    content = {
        "custom_attribute_values": [{
            "display_name": "",
            "attribute_object": None,
            "custom_attribute_id": 45,
            "context_id": None,
            "created_at": "2018-01-19T14:57:40",
            "attributable_type": "Control",
            "attribute_object_id": None,
            "updated_at": "2018-01-19T14:57:40",
            "modified_by": None,
            "modified_by_id": None,
            "attribute_value": "Super text",
            "type": "CustomAttributeValue",
            "id": 47,
            "attributable_id": 23
        }],

        "custom_attribute_definitions": [{
            "mandatory": None, "title": "sample_text_cad",
            "multi_choice_options": None,
            "created_at": "2018-01-19T14:57:39",
            "modified_by_id": None,
            "multi_choice_mandatory": None,
            "updated_at": "2018-01-19T14:57:39",
            "definition_id": None,
            "definition_type": "control",
            "modified_by": None,
            "helptext": None,
            "placeholder": None,
            "attribute_type": "Text",
            "context_id": None,
            "display_name": "sample_text_cad",
            "type": "CustomAttributeDefinition",
            "id": 45
        }]
    }

    dummy_ac_role_id = 10
    revision = all_models.Revision(obj, mock.Mock(), mock.Mock(), content)
    with mock.patch("ggrc.access_control.role.get_custom_roles_for",
                    return_value={dummy_ac_role_id: 'map_person_gca'}):
      result = revision.populate_acl_from_migrated_gcas()
      self.assertEqual(len(result['access_control_list']), 0)
      self.assertEqual(result['custom_attribute_definitions'],
                       content['custom_attribute_definitions'])
      self.assertEqual(result['custom_attribute_values'],
                       content['custom_attribute_values'])

  @ddt.data(
      ({}, {}),
      ({"custom_attribute_values": [], "custom_attributes": []}, {}),
      ({"custom_attributes": []}, {"custom_attribute_values": []}),
      ({"custom_attributes": [1, 2, 3]},
       {"custom_attribute_values": [1, 2, 3]}),
      ({"custom_attribute_values": [1, 2, 3]}, {}),
  )
  @ddt.unpack
  def test_populated_content_cavs(self, content, expected_content):
    """Test populated cavs content for revision if start content is {0}."""
    obj = mock.Mock()
    obj.id = self.object_id
    obj.__class__.__name__ = self.object_type
    revision = all_models.Revision(obj, mock.Mock(), mock.Mock(), content)
    self.assertEqual(expected_content, revision.populate_cavs())
