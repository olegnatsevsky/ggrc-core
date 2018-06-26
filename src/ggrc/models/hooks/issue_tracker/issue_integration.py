# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Module contains functionality for issue with issue tracker integration."""

# pylint: disable=unused-argument

import logging

logger = logging.getLogger(__name__)


def create_issue_handler(obj, **kwargs):
  """Event handler for issue object creation."""
  logger.info("Handle issue creation event")


def delete_issue_handler(obj, **kwargs):
  """Event handler for issue object deletion."""
  logger.info("Handle issue deletion event")


def update_issue_handler(obj, initial_state, **kwargs):
  """Event handler for issue object renewal."""
  logger.info("Handle issue renewal event")
