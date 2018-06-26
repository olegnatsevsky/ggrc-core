# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""This module contains hooks for issue tracker integration."""

# pylint: disable=unused-argument

from ggrc import settings
from ggrc.services import signals
from ggrc.models import all_models

from ggrc.models.hooks.issue_tracker import assessment_integration
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


def create_object_handler(sender, objects=None, **kwargs):
  """Common handler for 'collection_posted' event.
  Args:
      sender: A class of Resource handling the POST request.
      objects: A list of model instances created from the POSTed JSON.
      sources: A list of original POSTed JSON dictionaries.
  """
  for obj in objects:
    object_handlers = ISSUE_TRACKER_HANDLERS.get(sender, {})
    if CREATE_HANDLER_NAME in object_handlers:
      object_handlers[CREATE_HANDLER_NAME](obj)


def delete_object_handler(sender, obj=None, **kwargs):
  """Common handler for 'model_deleted' event.
  Args:
      sender: A class of Resource handling the DELETE request.
      obj: Model instance for deletion.
  """
  object_handlers = ISSUE_TRACKER_HANDLERS.get(sender, {})
  if DELETE_HANDLER_NAME in object_handlers:
    object_handlers[DELETE_HANDLER_NAME](obj)


def update_object_handler(sender, obj=None, initial_state=None, **kwargs):
  """Common handler for 'model_put' event.
  Args:
      sender: A class of Resource handling the PUT request.
      obj: Model instance for update.
  """
  object_handlers = ISSUE_TRACKER_HANDLERS.get(sender, {})
  if UPDATE_HANDLER_NAME in object_handlers:
    object_handlers[UPDATE_HANDLER_NAME](obj, initial_state)


def init_common_handlers():
  """Initialize common handlers for all models from handlers dict"""

  if not settings.ISSUE_TRACKER_ENABLED:
    return

  for model, model_handlers in ISSUE_TRACKER_HANDLERS.iteritems():
    if CREATE_HANDLER_NAME in model_handlers:
      signals.Restful.model_posted_after_commit.connect(
          create_object_handler,
          sender=model
      )

    if DELETE_HANDLER_NAME in model_handlers:
      signals.Restful.model_deleted.connect(
          delete_object_handler,
          sender=model
      )

    if UPDATE_HANDLER_NAME in model_handlers:
      signals.Restful.model_put_after_commit.connect(
          update_object_handler,
          sender=model
      )


def init_hook():
  """Initialize all hooks for issue tracker integration."""
  assessment_integration.init_hook()
  init_common_handlers()
