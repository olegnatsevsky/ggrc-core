# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Test Issue tracker query builder."""

# pylint: disable=protected-access

import unittest

import ddt
import mock

from ggrc.models import exceptions
from ggrc.models.hooks.issue_tracker import issue_tracker_query_builder


@ddt.ddt
class TestBaseIssueTrackerQueryBuilder(unittest.TestCase):
  """Test base class for issue tracker query builder."""

  def setUp(self):
    """Perform initialisation for each test cases."""
    self.builder = issue_tracker_query_builder.BaseIssueTrackerQueryBuilder()

  def test_adding_comments(self):
    """Test adding comments to issue tracker query."""
    # Arrange test data.
    test_comments = ["comment1", "comment2", "comment3", ]

    # Perform action.
    for comment in test_comments:
      self.builder.add_comment(comment)

    # Assert results.
    self.assertEqual(
        self.builder.get_joined_comments(),
        "\n".join(test_comments)
    )

  @ddt.data(
      # Test data for failure cases.
      ({"component_id": "not float number"}, None, exceptions.ValidationError),
      ({"hotlist_id": "not float number"}, None, exceptions.ValidationError),

      # Test data for Ok case.
      (
          {
              "component_id": "123",
              "hotlist_id": 321,
              "title": "test_title",
              "issue_type": "test_type",
              "issue_priority": "test_priority",
              "issue_severity": "test_severity",
          },
          {
              "component_id": 123,
              "hotlist_id": [321, ],
              "title": "test_title",
              "type": "test_type",
              "priority": "test_priority",
              "severity": "test_severity",
          },
          None
      )
  )
  @ddt.unpack
  def test_handle_issue_tracker_info(self, data, expected_result, error=None):
    """Test 'handle_issue_tracker_info' method."""
    if error:
      with self.assertRaises(error):
        self.builder.handle_issue_tracker_info(data)
    else:
      self.builder.handle_issue_tracker_info(data)
      result = self.builder.get_query()
      self.assertEquals(result, expected_result)


@ddt.ddt
class TestIssueQueryBuilder(unittest.TestCase):
  """Test issue tracker builder for iisue object."""

  def setUp(self):
    """Perform initialisation for each test cases."""
    self.builder = issue_tracker_query_builder.IssueQueryBuilder()

  def test_handle_issue_attributes(self):
    """Test '_handle_issue_attributes' method."""
    # pylint: disable=protected-access
    # Arrange test data.
    mock_object = mock.MagicMock()
    mock_object.description = "<p>test_description</p>"
    mock_object.test_plan = "<p>test_plan</p>"
    expected_result = (
        "Following is the issue Description from GGRC: test_description\n"
        "Following is the issue Remediation Plan from GGRC: test_plan"
    )

    # Perform action.
    self.builder._handle_issue_attributes(mock_object)

    # Assert results.
    self.assertEquals(self.builder.get_joined_comments(), expected_result)

  def test_set_issue_status(self):
    """Test 'set_issue_status' method."""
    # Arrange test data.
    test_status = "test_status"
    expected_result = {"status": test_status}

    # Perform action.
    self.builder.set_issue_status(test_status)

    # Assert results.
    self.assertEquals(self.builder.get_query(), expected_result)

  @ddt.data(
      # Test case 1.
      (
          {
              "Admin": [("admin_name", "verifier_email"), ],
              "Primary Contacts": [("assignee_name", "assignee_email"), ],
              "Custom Role": [],
              "modified_by": "reporter_email",
          },
          {
              "verifier": "verifier_email",
              "assignee": "assignee_email",
              "reporter": "reporter_email",
              "ccs": [],
          }
      ),

      # Test case 2.
      (
          {
              "Admin": [
                  ("verifier_name", "verifier_email_2"),
                  ("admin_name", "verifier_email_1"),
              ],
              "Primary Contacts": [
                  ("primary_contact_name", "assignee_email_2"),
                  ("assignee_name", "assignee_email_1"),
              ],
              "Custom Role": [
                  ("reporter_name", "reporter_email"),
                  ("custom_name", "custom_email"),
                  ("admin_name", "verifier_email_1"),
              ],
              "modified_by": "reporter_email",
          },
          {
              "verifier": "verifier_email_1",
              "assignee": "assignee_email_1",
              "reporter": "reporter_email",
              "ccs": ["custom_email", "assignee_email_2", "verifier_email_2"],
          }
      )
  )
  @ddt.unpack
  def test_handle_people_list(self, test_data, expected_result):
    """Test '_handle_people_list' method."""
    # Arrange test data.
    mock_object = mock.MagicMock()
    acls = []
    for role, person_data in test_data.iteritems():
      if role == "modified_by":
        mock_object.modified_by.email = test_data["modified_by"]
      else:
        for person_name, person_email in person_data:
          acl = mock.MagicMock()
          acl.ac_role.name = role
          acl.person.name = person_name
          acl.person.email = person_email

          acls.append(acl)

    mock_object.access_control_list = acls

    # Perform action.
    self.builder._handle_people_list(mock_object)

    # Assert results.
    self.assertDictEqual(self.builder.get_query(), expected_result)
