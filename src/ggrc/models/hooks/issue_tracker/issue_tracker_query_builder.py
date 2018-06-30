# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""This module contains functionality for building Issue tracker query."""

import urlparse

import html2text

from ggrc import utils as ggrc_utils
from ggrc.models.hooks.issue_tracker import integration_utils


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
      "Changes to this GGRC {model} will no longer be tracked within this bug."
  )

  ENABLE_TMPL = (
      "Changes to this GGRC {model} will be tracked within this bug."
  )

  COMMENT_TMPL = (
      'A new comment is added by {author} to the {model}: {comment}. '
      'Use the following to link to get more information from the '
      'GGRC {model}. Link - {link}'
  )

  def __init__(self):
    """Basic initialization."""
    self._issue_tracker_query = {}
    self._comments = []

  @staticmethod
  def get_ggrc_object_url(obj):
    """Builds and returns URL to GGRC object."""
    return urlparse.urljoin(
        ggrc_utils.get_url_root(),
        ggrc_utils.view_url_for(obj)
    )

  def get_query(self):
    """Returns query with issue tracker parameters."""
    return self._issue_tracker_query

  def add_comment(self, message):
    """Add comment into issue tracker issue."""
    self._comments.append(message)

  def get_joined_comments(self):
    """Returns str with joined comments."""
    return "\n".join(self._comments)

  def handle_issue_tracker_info(self, issue_tracker_info):
    """Handle issue tracker information."""
    integration_utils.validate_issue_tracker_info(issue_tracker_info)
    integration_utils.normalize_issue_tracker_info(issue_tracker_info)

    hotlist_id = issue_tracker_info.get('hotlist_id')

    self._issue_tracker_query.update({
        "component_id": issue_tracker_info.get("component_id", ""),
        "hotlist_id": [hotlist_id] if hotlist_id else [],
        "title": issue_tracker_info.get("title", ""),
        "type": issue_tracker_info.get("issue_type", ""),
        "priority": issue_tracker_info.get("issue_priority", ""),
        "severity": issue_tracker_info.get("issue_severity", "")
    })


class IssueQueryBuilder(BaseIssueTrackerQueryBuilder):
  """Issue tracker query builder for GGRC Issue object."""

  MODEL_NAME = "Issue"
  DESCRIPTION_TMPL = "Following is the issue Description from GGRC: {}"
  REMEDIATION_PLAN = "Following is the issue Remediation Plan from GGRC: {}"

  def build_create_query(self, obj, issue_tracker_info):
    """Build create issue query for issue tracker."""
    self.add_comment(self.INITIAL_COMMENT_TMPL.format(
        model=self.MODEL_NAME,
        link=self.get_ggrc_object_url(obj)
    ))
    self.handle_issue_tracker_info(issue_tracker_info)
    self._handle_people_list(obj)
    self._handle_issue_attributes(obj)
    self.set_issue_status("ASSIGNED")

    # Should be called in the end of building process because
    # some steps can adds comments inside methods.
    self._issue_tracker_query["comment"] = self.get_joined_comments()

    return self.get_query()

  def build_update_query(self):
    raise NotImplementedError

  def build_delete_query(self):
    raise NotImplementedError

  def _handle_people_list(self, obj):
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

    issue_verifier_email = admins.pop(0).email if admins else ""
    self._issue_tracker_query["verifier"] = issue_verifier_email

    # Handle Primary Contacts list.
    primary_contacts = [
        acl.person for acl in acls
        if acl.ac_role.name == "Primary Contacts"
    ]
    primary_contacts = sorted(primary_contacts, key=lambda p: p.name)
    assignee_email = primary_contacts.pop(0).email if primary_contacts else ""
    self._issue_tracker_query["assignee"] = assignee_email

    # Handle reporter list.
    reporter_email = obj.modified_by.email
    self._issue_tracker_query["reporter"] = reporter_email

    # Handle CCS list.
    all_other_persons = [
        acl.person for acl in acls
        if acl.ac_role.name not in ("Admin", "Primary Contacts")
    ]
    # We don't need to include persons in CCS if they emails
    # already in 'assignee', 'reporter' or 'verifier' fields.
    ccs_persons = set(all_other_persons) | set(admins) | set(primary_contacts)
    css_emails = {person.email for person in ccs_persons}
    css_emails -= {issue_verifier_email, assignee_email, reporter_email}
    self._issue_tracker_query["ccs"] = list(css_emails)

  def _handle_issue_attributes(self, obj):
    """Handle attributes from GGRC Issue object.

    This method adds Issue description and Remediation Plan as comments
    to Issue Tracker Issue.
    """
    description = obj.description
    if description:
      description = html2text.HTML2Text().handle(description).strip('\n')
      self.add_comment(self.DESCRIPTION_TMPL.format(description))

    test_plan = obj.test_plan
    if test_plan:
      test_plan = html2text.HTML2Text().handle(test_plan).strip('\n')
      self.add_comment(self.REMEDIATION_PLAN.format(test_plan))

  def set_issue_status(self, status):
    """Add issue status to query."""
    self._issue_tracker_query["status"] = status
