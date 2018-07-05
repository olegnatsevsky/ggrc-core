# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""This module contains common utils for integration functionality."""

from ggrc import settings
from ggrc.models import exceptions


def validate_issue_tracker_info(info):
  """Validates that component ID and hotlist ID are integers."""
  component_id = info.get('component_id')
  if component_id:
    try:
      int(component_id)
    except (TypeError, ValueError):
      raise exceptions.ValidationError('Component ID must be a number.')

  hotlist_id = info.get('hotlist_id')
  if hotlist_id:
    try:
      int(hotlist_id)
    except (TypeError, ValueError):
      raise exceptions.ValidationError('Hotlist ID must be a number.')


def normalize_issue_tracker_info(info):
  """Insures that component ID and hotlist ID are integers."""
  # TODO(anushovan): remove data type casting once integration service
  #   supports strings for following properties.
  component_id = info.get('component_id')
  if component_id:
    try:
      info['component_id'] = int(component_id)
    except (TypeError, ValueError):
      raise exceptions.ValidationError('Component ID must be a number.')

  hotlist_id = info.get('hotlist_id')
  if hotlist_id:
    try:
      info['hotlist_id'] = int(hotlist_id)
    except (TypeError, ValueError):
      raise exceptions.ValidationError('Hotlist ID must be a number.')


def build_issue_tracker_url(issue_id):
  """Build issue tracker URL by issue id."""
  issue_tracker_tmpl = settings.ISSUE_TRACKER_BUG_URL_TMPL
  url_tmpl = issue_tracker_tmpl if issue_tracker_tmpl else 'http://issue/%s'
  return url_tmpl % issue_id
