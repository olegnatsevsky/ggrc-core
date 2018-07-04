# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""This module contains hooks for issue tracker integration."""

from ggrc.models.hooks.issue_tracker import assessment_integration
from ggrc.models.hooks.issue_tracker import common_handlers


def init_hook():
  """Initialize all hooks for issue tracker integration."""
  assessment_integration.init_hook()
  common_handlers.init_hook()
