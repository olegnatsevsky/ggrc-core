# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Review model."""
import datetime

import sqlalchemy as sa

from ggrc import db, login
from ggrc import builder
from ggrc.models import mixins
from ggrc.models import utils as model_utils
from ggrc.models import reflection
from sqlalchemy.orm import validates

from ggrc.models.mixins import issue_tracker
from ggrc.fulltext import mixin as ft_mixin
from ggrc.access_control import roleable

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
    return super(Reviewable, cls).eager_query(sa.orm.joinedload("review"))


class Review(mixins.person_relation_factory("last_reviewed_by"),
             mixins.person_relation_factory("created_by"),
             mixins.datetime_mixin_factory("last_reviewed_at"),
             mixins.Stateful,
             roleable.Roleable,
             issue_tracker.IssueTracked,
             Relatable,
             mixins.base.ContextRBAC,
             mixins.Base,
             ft_mixin.Indexed,
             db.Model):

  def __init__(self, *args, **kwargs):
    super(Review, self).__init__(*args, **kwargs)
    self.last_reviewed_at = None
    self.last_reviewed_by = None

  __tablename__ = "reviews"

  class STATES(object):
    REVIEWED = "Reviewed"
    UNREVIEWED = "Unreviewed"

  VALID_STATES = [STATES.UNREVIEWED, STATES.REVIEWED]

  class ACRoles(object):
    REVIEWER = "Reviewer"
    REVIEWABLE_READER = "Reviewable Reader"
    REVIEW_EDITOR = "Review Editor"

  class NotificationContext(object):

      class Types(object):
          EMAIL_TYPE = "email"
          ISSUE_TRACKER = "issue_tracker"

  reviewable_id = db.Column(db.Integer, nullable=False)
  reviewable_type = db.Column(db.String, nullable=False)

  REVIEWABLE_TMPL = "{}_reviewable"

  reviewable = model_utils.json_polimorphic_relationship_factory(
      Reviewable
  )(
      "reviewable_id", "reviewable_type", REVIEWABLE_TMPL
  )

  notification_type = db.Column(
      sa.types.Enum(NotificationContext.Types.EMAIL_TYPE,
                    NotificationContext.Types.ISSUE_TRACKER),
      nullable=False,
  )
  email_message = db.Column(db.Text, nullable=False, default=u"")

  _api_attrs = reflection.ApiAttributes(
      "notification_type",
      "email_message",
      reflection.Attribute("reviewable", update=False),
      reflection.Attribute("last_reviewed_by", update=False),
      reflection.Attribute("last_reviewed_at", update=False),
      "issuetracker_issue",
      "status",
  )

  _fulltext_attrs = [
      "reviewable_id",
      "reviewable_type",
  ]

  @validates("status")
  def validate_status(self, key, value):
    super_class = super(Review, self)
    if hasattr(super_class, "validate_status"):
      value = super_class.validate_status(key, value)
    if value == Review.STATES.REVIEWED:
      self.last_reviewed_at = datetime.datetime.now()
      self.last_reviewed_by = login.get_current_user()
    return value

