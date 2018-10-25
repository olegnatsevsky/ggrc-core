# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Helpers for review tests"""
from ggrc.models import all_models
from integration.ggrc import generator


def build_reviewer_acl(acr_id=None, user_id=None):
  """Build reviewer acl list from passed values of create new user"""
  if not acr_id:
    acr_id = all_models.AccessControlRole.query.filter_by(
        name="Reviewer", object_type="Review"
    ).one().id

  if not user_id:
    user_id = all_models.Person.query.filter_by(
        email="user@example.com"
    ).one().id

  return [{
      "ac_role_id": acr_id,
      "person": {
          "id": user_id
      },
  }]


def generate_review_object(
        instance,
        state=all_models.Review.STATES.UNREVIEWED,
        notification_type=all_models.Review.NotificationTypes.EMAIL_TYPE):
  """
  Generates Review for model.

  Args:
      instance: Factory instance
      state: Review state, unreviewed by default
      notification_type: Notification type, email by default

  Returns:
    Response and Review
  """
  instance = instance.query.get(instance.id)
  return generator.ObjectGenerator().generate_object(
      all_models.Review,
      {
          "reviewable": {
              "type": instance.type,
              "id": instance.id,
          },
          "context": None,
          "notification_type": notification_type,
          "status": state,
          "access_control_list": build_reviewer_acl(),
      },
  )
