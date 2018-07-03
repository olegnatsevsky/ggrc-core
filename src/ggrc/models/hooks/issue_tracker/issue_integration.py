# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Module contains functionality for issue with issue tracker integration."""

# pylint: disable=unused-argument

import logging


from ggrc import db
from ggrc.integrations import issues
from ggrc.integrations import integrations_errors
from ggrc.models import all_models
from ggrc.models.hooks.issue_tracker import issue_tracker_query_builder
from ggrc.models.hooks.issue_tracker import integration_utils

logger = logging.getLogger(__name__)


def create_issue_handler(obj, issue_tracker_info):
  """Event handler for issue object creation."""
  if not issue_tracker_info or not issue_tracker_info.get("enabled"):
    return

  # We need in flush here because we need object id for URL generation.
  db.session.flush()

  builder = issue_tracker_query_builder.IssueQueryBuilder()
  issue_tracker_query = builder.build_create_query(obj, issue_tracker_info)

  # Try to create issue in issue tracker.
  try:
    res = issues.Client().create_issue(issue_tracker_query)

    issue_url = integration_utils.build_issue_tracker_url(res["issueId"])
    issue_tracker_info["issue_url"] = issue_url
    issue_tracker_info["issue_id"] = res["issueId"]
  except integrations_errors.Error as error:
    logger.error(
        "Unable to create a ticket while creating object ID=%d: %s",
        obj.id, error
    )
    issue_tracker_info["enabled"] = False

  # Fill necessary fields for issuetracker_issue object.
  issue_tracker_info["cc_list"] = issue_tracker_query["ccs"]
  issue_tracker_info["assignee"] = issue_tracker_query["assignee"]

  # Create object in GGRC with info about issue tracker integration.
  all_models.IssuetrackerIssue.create_or_update_from_dict(
      obj, issue_tracker_info
  )

def delete_issue_handler(obj, **kwargs):
  """Event handler for issue object deletion."""
  logger.info("Handle issue deletion event")


def update_issue_handler(obj, initial_state, **kwargs):
  """Event handler for issue object renewal."""
  logger.info("Handle issue renewal event")
