# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Review model."""


import sqlalchemy as sa

from ggrc import db
from ggrc import builder
from ggrc.models import mixins
from ggrc.models import utils as model_utils
from ggrc.models import reflection
from ggrc.models import issuetracker_issue
from ggrc.fulltext import mixin as ft_mixin
from ggrc.access_control import roleable
from ggrc.models.relationship import Relatable


class Reviewable(object):
  """Mixin to setup instance as reviewable."""

  # REST properties
  _api_attrs = reflection.ApiAttributes(
      reflection.Attribute('review', create=False, update=False),
      reflection.Attribute('review_status', create=False, update=False),
      reflection.Attribute('review_issue_link', create=False, update=False),
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
    """Declare review relationship for reviewable instance."""

    def join_function():
        return sa.and_(sa.orm.foreign(Review.instance_type) == cls.__name__,
                       sa.orm.foreign(Review.instance_id) == cls.id)

    return sa.orm.relationship(
        Review,
        primaryjoin=join_function,
        backref=Review.INSTANCE_TMPL.format(cls.__name__),
        uselist=False,
    )

  @classmethod
  def eager_query(cls):
    return super(Reviewable, cls).eager_query(orm.joinedload('review'))


class Review(mixins.person_relation_factory("last_set_reviewed_by"),
             mixins.person_relation_factory("last_set_unreviewed_by"),
             mixins.person_relation_factory("created_by"),
             mixins.datetime_mixin_factory("last_set_reviewed_at"),
             mixins.datetime_mixin_factory("last_set_unreviewed_at"),
             mixins.Stateful,
             roleable.Roleable,
             issuetracker_issue.IssueTracked,
             Relatable,
             mixins.Base,
             ft_mixin.Indexed,
             db.Model):

  __tablename__ = 'reviews'

  class ACRoles(object):
      REVIEWER = 'Reviewer'
      REVIEWABLE_READER = 'Reviewable Reader'
      REVIEW_EDITOR = 'Review Editor'

  class STATES(object):
      REVIEWED = 'Reviewed'
      UNREVIEWED = 'Unreviewed'

  VALID_STATES = [STATES.UNREVIEWED, STATES.REVIEWED]

  class NotificationContext(object):

      class Types(object):
          EMAIL_TYPE = "email"
          ISSUE_TRACKER = "issue_tracker"


  instance_id = db.Column(db.Integer, nullable=False)
  instance_type = db.Column(db.String, nullable=False)

  INSTANCE_TMPL = "{}_reviewable"

  instance = model_utils.json_polimorphic_relationship_factory(
      Reviewable
  )(
      "instance_id", "instance_type", INSTANCE_TMPL
  )

  notification_type = db.Column(
      sa.types.Enum(NotificationContext.Types.EMAIL_TYPE,
                    NotificationContext.Types.ISSUE_TRACKER),
      nullable=False,
  )
  email_message = db.Column(db.Text, nullable=False, default=u"")
  # small agenda, it will highlight human readable state of object
  agenda = db.Column(db.Text, nullable=False, default="")

  _api_attrs = reflection.ApiAttributes(
      'notification_type',
      'email_message',
      reflection.Attribute('instance', update=False),
      'issuetracker_issue',
      reflection.Attribute('agenda', create=False, update=False),
      'status',
  )

  _fulltext_attrs = [
      "instance_id",
      "instance_type",
      "agenda",
  ]
