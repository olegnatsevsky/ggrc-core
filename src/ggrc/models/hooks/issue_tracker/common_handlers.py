# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""This module contains common handlers for issue tracker integration."""

# pylint: disable=unused-argument

import itertools

from ggrc import settings
from ggrc.models.hooks.issue_tracker import handlers_mapping
from ggrc.services import signals


def create_object_handler(sender, objects=None, **kwargs):
  """Common handler for 'collection_posted' event.
  Args:
      sender: A class of Resource handling the POST request.
      objects: A list of model instances created from the POSTed JSON.
      sources: A list of original POSTed JSON dictionaries.
  """
  sources = kwargs.get("sources", [])
  for obj, src in itertools.izip(objects, sources):
    object_handlers = handlers_mapping.ISSUE_TRACKER_HANDLERS.get(sender, {})
    issue_tracker_info = src.get("issue_tracker", {}) if src else {}
    object_handlers[handlers_mapping.CREATE_HANDLER_NAME](obj,
                                                          issue_tracker_info)


def delete_object_handler(sender, obj=None, **kwargs):
  """Common handler for 'model_deleted' event.
  Args:
      sender: A class of Resource handling the DELETE request.
      obj: Model instance for deletion.
  """
  object_handlers = handlers_mapping.ISSUE_TRACKER_HANDLERS.get(sender, {})
  object_handlers[handlers_mapping.DELETE_HANDLER_NAME](obj)


def update_object_handler(sender, obj=None, initial_state=None, **kwargs):
  """Common handler for 'model_put' event.
  Args:
      sender: A class of Resource handling the PUT request.
      obj: Model instance for update.
  """
  object_handlers = handlers_mapping.ISSUE_TRACKER_HANDLERS.get(sender, {})
  issue_tracker = kwargs.get("src", {}).get("issue_tracker")
  object_handlers[handlers_mapping.UPDATE_HANDLER_NAME](obj,
                                                        initial_state,
                                                        issue_tracker)


def init_hook():
  """Initialize common handlers for all models from handlers dict."""

  if not settings.ISSUE_TRACKER_ENABLED:
    return

  issue_tracker_handlers = handlers_mapping.ISSUE_TRACKER_HANDLERS
  for model, model_handlers in issue_tracker_handlers.iteritems():
    if handlers_mapping.CREATE_HANDLER_NAME in model_handlers:
      signals.Restful.collection_posted.connect(
          create_object_handler,
          sender=model
      )

    if handlers_mapping.DELETE_HANDLER_NAME in model_handlers:
      signals.Restful.model_deleted.connect(
          delete_object_handler,
          sender=model
      )

    if handlers_mapping.UPDATE_HANDLER_NAME in model_handlers:
      signals.Restful.model_put_after_commit.connect(
          update_object_handler,
          sender=model
      )
