# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""  Review helpers """
import collections

from ggrc.models import all_models

from ggrc import db
from ggrc.notifications.common import create_notification_history_obj
from ggrc.notifications.data_handlers import get_object_url

REVIEW_REQUEST_CREATED = "review_request_created"

EmailReviewContext = collections.namedtuple(
    "EmailReviewContext", ["reviewable", "object_url", "email_message"]
)


def get_review_notifications():
  return all_models.Notification.query.filter(
      all_models.Notification.object_type == all_models.Review.__name__,
      all_models.Notification.runner == all_models.Notification.RUNNER_FAST
  )


def build_review_data(review_notifications):
  reviewers_data = collections.defaultdict(dict)

  for notification in review_notifications:
    review = notification.object
    reviewable = review.reviewable
    link = get_object_url(reviewable)
    for acl in review.access_control_list:
      context = EmailReviewContext(reviewable,
                                   link,
                                   review.email_message)
      reviewers_data[acl.person][review.id] = context
  return reviewers_data


def move_notifications_to_history(notifications):
  for notification in notifications:
    notif_history = create_notification_history_obj(notification)
    db.session.add(notif_history)
    db.session.delete(notification)
