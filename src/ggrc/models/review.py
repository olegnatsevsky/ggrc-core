# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Review model."""
import datetime

import sqlalchemy as sa

from ggrc import db
from ggrc import builder
from ggrc.models import mixins
from ggrc.models import utils as model_utils
from ggrc.models import reflection

from ggrc.models.mixins import issue_tracker
from ggrc.fulltext import mixin as ft_mixin
from ggrc.access_control import roleable

from ggrc.models.mixins.before_flush_handleable import BeforeFlushHandleable
from ggrc.models.relationship import Relatable


class Reviewable(object):
  """Mixin to setup object as reviewable."""

  # REST properties
  _api_attrs = reflection.ApiAttributes(
      reflection.Attribute("review", create=False, update=False),
      reflection.Attribute("review_status", create=False, update=False),
      reflection.Attribute("review_issue_link", create=False, update=False),
  )

  _fulltext_attrs = ["review_status", "review_issue_link"]

  @builder.simple_property
  def review_status(self):
    return self.review.status if self.review else Review.STATES.UNREVIEWED

  @builder.simple_property
  def review_issue_link(self):
    """Returns review issue link for reviewable object."""
    if not self.review:
      return None
    if not self.review.issuetracker_issue:
      return None
    notification_type = self.review.notification_type
    if not notification_type == self.NotificationContext.Types.ISSUE_TRACKER:
      return None
    return self.review.issuetracker_issue.issue_url

  @sa.ext.declarative.declared_attr
  def review(cls):  # pylint: disable=no-self-argument
    """Declare review relationship for reviewable object."""

    def join_function():
      return sa.and_(sa.orm.foreign(Review.reviewable_type) == cls.__name__,
                     sa.orm.foreign(Review.reviewable_id) == cls.id)

    return sa.orm.relationship(
        Review,
        primaryjoin=join_function,
        backref=Review.REVIEWABLE_TMPL.format(cls.__name__),
        uselist=False,
    )

  @classmethod
  def eager_query(cls):
    return super(Reviewable, cls).eager_query().options(
        sa.orm.joinedload("review")
    )

  def log_json(self):
    """Serialize to JSON"""
    out_json = super(Reviewable, self).log_json()
    out_json["review_status"] = self.review_status
    return out_json


class Review(mixins.person_relation_factory("last_reviewed_by"),
             mixins.person_relation_factory("created_by"),
             mixins.datetime_mixin_factory("last_reviewed_at"),
             mixins.Stateful,
             BeforeFlushHandleable,
             roleable.Roleable,
             issue_tracker.IssueTracked,
             Relatable,
             mixins.base.ContextRBAC,
             mixins.Base,
             ft_mixin.Indexed,
             db.Model):
  """Review object"""
  # pylint: disable=too-few-public-methods
  __tablename__ = "reviews"

  class STATES(object):
    """Review states container """
    REVIEWED = "Reviewed"
    UNREVIEWED = "Unreviewed"

  VALID_STATES = [STATES.UNREVIEWED, STATES.REVIEWED]

  class ACRoles(object):
    """ACR roles container """
    REVIEWER = "Reviewer"
    REVIEWABLE_READER = "Reviewable Reader"
    REVIEW_EDITOR = "Review Editor"

  class NotificationTypes(object):
    """Notification types container """
    EMAIL_TYPE = "email"
    ISSUE_TRACKER = "issue_tracker"

  reviewable_id = db.Column(db.Integer, nullable=False)
  reviewable_type = db.Column(db.String, nullable=False)

  REVIEWABLE_TMPL = "{}_reviewable"

  reviewable = model_utils.json_polymorphic_relationship_factory(
      Reviewable
  )(
      "reviewable_id", "reviewable_type", REVIEWABLE_TMPL
  )

  notification_type = db.Column(
      sa.types.Enum(NotificationTypes.EMAIL_TYPE,
                    NotificationTypes.ISSUE_TRACKER),
      nullable=False,
  )
  email_message = db.Column(db.Text, nullable=False, default=u"")

  _api_attrs = reflection.ApiAttributes(
      "notification_type",
      "email_message",
      reflection.Attribute("reviewable", update=False),
      reflection.Attribute("last_reviewed_by", create=False, update=False),
      reflection.Attribute("last_reviewed_at", create=False, update=False),
      "issuetracker_issue",
      "status",
  )

  _fulltext_attrs = [
      "reviewable_id",
      "reviewable_type",
  ]

  def handle_before_flush(self):
    """Override with custom handling"""
    self._create_relationship()
    self._update_reviewed_by()

  def _create_relationship(self):
    """Create relationship for newly created review (used for ACL)"""
    from ggrc.models import all_models
    if self in db.session.new:
      db.session.add(
          all_models.Relationship(source=self.reviewable, destination=self)
      )

  def _update_reviewed_by(self):
    """Update last_reviewed_by, last_reviewed_at"""
    # pylint: disable=attribute-defined-outside-init
    from ggrc.models import all_models
    if not db.inspect(self).attrs["status"].history.has_changes():
      return

    self.reviewable.updated_at = datetime.datetime.now()

    if self.status == all_models.Review.STATES.REVIEWED:
      self.last_reviewed_by = self.modified_by
      self.last_reviewed_at = datetime.datetime.now()
