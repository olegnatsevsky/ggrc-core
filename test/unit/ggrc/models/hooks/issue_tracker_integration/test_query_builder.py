# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Test Issue tracker query builder."""

# pylint: disable=protected-access
# pylint: disable=invalid-name

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

  @ddt.data(
      {"component_id": "not float number"},
      {"hotlist_id": "not float number"},
  )
  def test_handle_issue_tracker_info_for_failure(self, issue_tracker_info):
    """Test 'handle_issue_tracker_info' method for failure cases."""
    with self.assertRaises(exceptions.ValidationError):
      self.builder.handle_issue_tracker_info(issue_tracker_info)

  def test_handle_issue_tracker_info(self):
    """Test 'handle_issue_tracker_info' method."""
    # Arrange test data.
    issue_tracker_info = {
        "component_id": "123",
        "hotlist_id": 321,
        "title": "test_title",
        "issue_type": "test_type",
        "issue_priority": "test_priority",
        "issue_severity": "test_severity",
    }
    expected_result = {
        "component_id": 123,
        "hotlist_id": [321, ],
        "title": "test_title",
        "type": "test_type",
        "priority": "test_priority",
        "severity": "test_severity",
    }

    # Perform action.
    self.builder.handle_issue_tracker_info(issue_tracker_info)

    # Assert results.
    self.assertEquals(self.builder.issue_tracker_query, expected_result)


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
    expected_result = [
        "Following is the issue Description from GGRC: test_description",
        "Following is the issue Remediation Plan from GGRC: test_plan"
    ]

    # Perform action.
    self.builder._handle_issue_attributes(mock_object)

    # Assert results.
    self.assertEquals(self.builder.comments, expected_result)

  def test_handle_people_emails_without_ccs(self):
    """Test '_handle_people_emails' method without emails in ccs list."""
    mock_object = mock.MagicMock()
    mock_object.modified_by.email = "reporter_email"

    verifier = mock.MagicMock()
    verifier.person.name = "admin_name"
    verifier.person.email = "verifier_email"
    verifier.ac_role.name = "Admin"

    assignee = mock.MagicMock()
    assignee.person.name = "assignee_name"
    assignee.person.email = "assignee_email"
    assignee.ac_role.name = "Primary Contacts"

    mock_object.access_control_list = [verifier, assignee, ]

    expected_result = {
        "verifier": "verifier_email",
        "assignee": "assignee_email",
        "reporter": "reporter_email",
        "ccs": [],
    }

    # Perform action.
    self.builder._handle_people_emails(mock_object)

    # Assert results.
    self.assertDictEqual(self.builder.issue_tracker_query, expected_result)

  def test_handle_people_emails_with_ccs(self):
    """Test '_handle_people_emails' method with emails in ccs list."""
    mock_object = mock.MagicMock()
    mock_object.modified_by.email = "reporter_email"

    verifier_1 = mock.MagicMock()
    verifier_1.person.name = "admin_name"
    verifier_1.person.email = "verifier_email_1"
    verifier_1.ac_role.name = "Admin"

    verifier_2 = mock.MagicMock()
    verifier_2.person.name = "verifier_name"
    verifier_2.person.email = "verifier_email_2"
    verifier_2.ac_role.name = "Admin"

    assignee_1 = mock.MagicMock()
    assignee_1.person.name = "assignee_name"
    assignee_1.person.email = "assignee_email_1"
    assignee_1.ac_role.name = "Primary Contacts"

    assignee_2 = mock.MagicMock()
    assignee_2.person.name = "primary_contact_name"
    assignee_2.person.email = "assignee_email_2"
    assignee_2.ac_role.name = "Primary Contacts"

    custom_role_1 = mock.MagicMock()
    custom_role_1.person.name = "reporter_name"
    custom_role_1.person.email = "reporter_email"
    custom_role_1.ac_role.name = "Custom Role"

    custom_role_2 = mock.MagicMock()
    custom_role_2.person.name = "custom_name"
    custom_role_2.person.email = "custom_email"
    custom_role_2.ac_role.name = "Custom Role"

    custom_role_3 = mock.MagicMock()
    custom_role_3.person.name = "admin_name"
    custom_role_3.person.email = "verifier_email_1"
    custom_role_3.ac_role.name = "Custom Role"

    mock_object.access_control_list = [
        verifier_1,
        verifier_2,
        assignee_1,
        assignee_2,
        custom_role_1,
        custom_role_2,
        custom_role_3,
    ]

    expected_result = {
        "verifier": "verifier_email_1",
        "assignee": "assignee_email_1",
        "reporter": "reporter_email",
        "ccs": ["custom_email", "assignee_email_2", "verifier_email_2"],
    }

    # Perform action.
    self.builder._handle_people_emails(mock_object)

    # Assert results.
    self.assertDictEqual(self.builder.issue_tracker_query, expected_result)
