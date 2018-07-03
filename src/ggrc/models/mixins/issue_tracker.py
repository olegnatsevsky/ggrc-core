# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Mixins for issue tracker integration functionality."""

import sqlalchemy as sa
from sqlalchemy.ext.declarative import declared_attr

from ggrc.models import reflection
from ggrc.models import issuetracker_issue
from ggrc.models.issuetracker_issue import IssuetrackerIssue

from ggrc.builder import simple_property


class IssueTracked(object):
  """IssueTracked mixin.

  Defines a backref in IssueTrackerIssue model named ModelName_issue_tracked.
  """
  # pylint: disable=too-few-public-methods

  _api_attrs = reflection.ApiAttributes(
      reflection.Attribute('issue_tracker', create=False, update=False),
  )

  @declared_attr
  def issuetracker_issue(cls):  # pylint: disable=no-self-argument
    """Relationship with the corresponding issue for cls."""

    def join_function():
      """Object and Notification join function."""
      object_id = sa.orm.foreign(IssuetrackerIssue.object_id)
      object_type = sa.orm.foreign(IssuetrackerIssue.object_type)
      return sa.and_(object_type == cls.__name__,
                     object_id == cls.id)

    return sa.orm.relationship(
        IssuetrackerIssue,
        primaryjoin=join_function,
        backref="{}_issue_tracked".format(cls.__name__),
        cascade='all, delete-orphan',
    )

  @simple_property
  def issue_tracker(cls):  # pylint: disable=no-self-argument
    """Returns representation of issue tracker related info as a dict."""
    issue_info = issuetracker_issue.IssuetrackerIssue.get_issue(
        cls.type, cls.id
    )
    return issue_info.to_dict(include_issue=True) if issue_info else {}
