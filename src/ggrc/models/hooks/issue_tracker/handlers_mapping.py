# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""This module contains issue tracker handlers mapping."""

from ggrc.models import all_models
from ggrc.models.hooks.issue_tracker import issue_integration


CREATE_HANDLER_NAME = "create"
DELETE_HANDLER_NAME = "delete"
UPDATE_HANDLER_NAME = "update"


ISSUE_TRACKER_HANDLERS = {
    all_models.Issue: {
        CREATE_HANDLER_NAME: issue_integration.create_issue_handler,
        DELETE_HANDLER_NAME: issue_integration.delete_issue_handler,
        UPDATE_HANDLER_NAME: issue_integration.update_issue_handler,
    }
}
