# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""This module contains functionality for building Issue tracker query."""

# pylint: disable=invalid-name

import urlparse

import html2text

from ggrc import utils as ggrc_utils
from ggrc.models.hooks.issue_tracker import integration_utils
from ggrc.utils.custom_dict import MissingKeyDict


class BaseIssueTrackerQueryBuilder(object):
  """Base issue tracker query builder class.

  This class and all classes which inherits from it provide
  functionality for building query to issue tracker.
  So, this classes encapsulate business logic for mapping GGRC objects fields
  to issue tracker issue fields.
  """

  INITIAL_COMMENT_TMPL = (
      "This bug was auto-generated to track a GGRC {model}. "
      "Use the following link to find the {model} - {link}."
  )

  DISABLE_TMPL = (
      "Changes to this GGRC object will no longer be tracked within this bug."
  )

  ENABLE_TMPL = (
      "Changes to this GGRC object will be tracked within this bug."
  )

  COMMENT_TMPL = (
      "A new comment is added by {author} to the {model}: {comment}. "
      "Use the following to link to get more information from the "
      "GGRC {model}. Link - {link}"
  )

  ISSUE_TRACKER_INFO_FIELDS_TO_CHECK = (
      "component_id",
      "hotlist_id",
      "issue_severity",
      "issue_priority",
  )

  ISSUE_TRACKER_NAME_MAPPING = MissingKeyDict({
      "issue_severity": "severity",
      "issue_priority": "priority"
  })

  def __init__(self):
    """Basic initialization."""
    self.issue_tracker_query = {}
    self.comments = []

  @staticmethod
  def get_ggrc_object_url(obj):
    """Builds and returns URL to GGRC object."""
    return urlparse.urljoin(
        ggrc_utils.get_url_root(),
        ggrc_utils.view_url_for(obj)
    )

  def handle_issue_tracker_info(self, issue_tracker_info):
    """Handle issue tracker information."""
    integration_utils.normalize_issue_tracker_info(issue_tracker_info)

    hotlist_id = issue_tracker_info.get("hotlist_id")
    self.issue_tracker_query.update({
        "component_id": issue_tracker_info.get("component_id", ""),
        "hotlist_id": [hotlist_id] if hotlist_id else [],
        "title": issue_tracker_info.get("title", ""),
        "type": issue_tracker_info.get("issue_type", ""),
        "priority": issue_tracker_info.get("issue_priority", ""),
        "severity": issue_tracker_info.get("issue_severity", "")
    })

  def _update_issue_tracker_info(self, new_issue_tracker_info,
                                 current_issue_tracker_info):
    """Update issue tracker information."""

    difference_dict = self._build_difference_dict(new_issue_tracker_info,
                                                  current_issue_tracker_info)
    self.issue_tracker_query.update(difference_dict)

  def _build_difference_dict(self, new_data, old_data):
    """Create dict of attributes with changed values

    Rename dict keys according to Issue tracker name mapping
    """

    fields_to_check = self.ISSUE_TRACKER_INFO_FIELDS_TO_CHECK
    name_mapping = self.ISSUE_TRACKER_NAME_MAPPING
    res = {}
    for field in fields_to_check:
      new_value = new_data.get(field)
      old_value = old_data.get(field)
      if new_value != old_value:
        res[name_mapping[field]] = new_value
    return res


class IssueQueryBuilder(BaseIssueTrackerQueryBuilder):
  """Issue tracker query builder for GGRC Issue object."""

  MODEL_NAME = "Issue"
  DESCRIPTION_TMPL = "Following is the issue Description from GGRC: {}"
  REMEDIATION_PLAN_TMPL = (
      "Following is the issue Remediation Plan from GGRC: {}"
  )
  UPDATE_DESCRIPTION_TMPL = (
      "Issue Description has been updated.\n{}"
  )
  UPDATE_REMEDIATION_PLAN_TMPL = (
      "Issue Remediation Plan has been updated.\n{}"
  )

  def build_create_query(self, obj, issue_tracker_info):
    """Build create issue query for issue tracker."""
    self.comments.append(self.INITIAL_COMMENT_TMPL.format(
        model=self.MODEL_NAME,
        link=self.get_ggrc_object_url(obj)
    ))
    self.handle_issue_tracker_info(issue_tracker_info)
    self._handle_people_emails(obj)
    self._handle_issue_attributes(obj)
    self.issue_tracker_query["status"] = "ASSIGNED"

    # Should be executed in the end of building process because
    # some steps can adds comments inside methods.
    self.issue_tracker_query["comment"] = "\n\n".join(self.comments)

    return self.issue_tracker_query

  def build_update_query(self, obj, initial_state, new_issue_tracker_info,
                         current_issue_tracker_info):
    """Build update issue query for issue tracker."""

    if (not new_issue_tracker_info["enabled"] and
            not current_issue_tracker_info["enabled"]):
      return {}

    self._update_issue_comment_attributes(obj, initial_state,
                                          new_issue_tracker_info,
                                          current_issue_tracker_info)

    self._update_issue_tracker_info(new_issue_tracker_info,
                                    current_issue_tracker_info)

    if self.comments:
      self.issue_tracker_query["comment"] = "\n\n".join(self.comments)

    return self.issue_tracker_query

  def build_delete_query(self):
    """Build delete issue query for issue tracker."""
    self.comments.append(self.DISABLE_TMPL.format(model="Issue"))
    self.issue_tracker_query["status"] = "OBSOLETE"

    # Should be executed in the end of building process because
    # some steps can adds comments inside methods.
    self.issue_tracker_query["comment"] = "\n\n".join(self.comments)

    return self.issue_tracker_query

  def _handle_people_emails(self, obj):
    """Handle emails.

    Reporter should be a person who triggers an event.
    Verifier should be first person from Admins in alphabetical order.
    Assignee should be first person from Primary Contacts
             in alphabetical order.
    CCS should be all other persons that mentioned in custom roles.
    """
    acls = obj.access_control_list

    # Handle Admins list.
    admins = [acl.person for acl in acls if acl.ac_role.name == "Admin"]
    admins = sorted(admins, key=lambda person: person.name)

    issue_verifier_email = admins[0].email if admins else ""
    self.issue_tracker_query["verifier"] = issue_verifier_email

    # Handle Primary Contacts list.
    primary_contacts = [
        acl.person for acl in acls
        if acl.ac_role.name == "Primary Contacts"
    ]
    primary_contacts = sorted(primary_contacts, key=lambda p: p.name)
    assignee_email = primary_contacts[0].email if primary_contacts else ""
    self.issue_tracker_query["assignee"] = assignee_email

    # Handle reporter list.
    reporter_email = obj.modified_by.email
    self.issue_tracker_query["reporter"] = reporter_email

    # Handle CCS list.
    emails = {acl.person.email for acl in acls}
    emails -= {issue_verifier_email, assignee_email, reporter_email}
    self.issue_tracker_query["ccs"] = list(emails)

  def _handle_issue_attributes(self, obj):
    """Handle attributes from GGRC Issue object.

    This method adds Issue description and Remediation Plan as comments
    to Issue Tracker Issue.
    """
    description = obj.description
    if description:
      description = html2text.HTML2Text().handle(description).strip("\n")
      self.comments.append(self.DESCRIPTION_TMPL.format(description))

    test_plan = obj.test_plan
    if test_plan:
      test_plan = html2text.HTML2Text().handle(test_plan).strip("\n")
      self.comments.append(self.REMEDIATION_PLAN_TMPL.format(test_plan))

  def _update_issue_comment_attributes(self, obj, initial_state,
                                       new_issue_tracker_info,
                                       current_issue_tracker_info):
    """Update issue tracker comments"""
    description = obj.description
    initial_description = initial_state.description
    if description != initial_description:
      description = html2text.HTML2Text().handle(description).strip("\n")
      self.comments.append(self.UPDATE_DESCRIPTION_TMPL.format(description))

    test_plan = obj.test_plan
    initial_test_plan = initial_state.test_plan
    if test_plan != initial_test_plan:
      test_plan = html2text.HTML2Text().handle(test_plan).strip("\n")
      self.comments.append(self.UPDATE_REMEDIATION_PLAN_TMPL.format(test_plan))

    old_enabled = current_issue_tracker_info["enabled"]
    new_enabled = new_issue_tracker_info["enabled"]
    if old_enabled != new_enabled:
      enabled = new_enabled["enabled"]
      comment = self.ENABLE_TMPL if enabled else self.DISABLE_TMPL
      self.comments.append(comment)
