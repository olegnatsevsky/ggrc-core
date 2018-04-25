# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Review object hooks."""
from datetime import datetime

from ggrc.services import signals
from ggrc.models import all_models
from ggrc import db
from ggrc.models import review
from sqlalchemy import event


EXCLUDE_REVIEW_FIELDS = ["review"]


def update_review_status_on_reviewable_update(sender, obj=None,
                                              src=None, service=None,
                                              event=None,
                                              initial_state=None):  # noqa
  if not obj:
    return
  if not obj.review:
    return
  if obj.review.status == all_models.Review.STATES.UNREVIEWED:
    return
  if any([a.history.has_changes() for a in db.inspect(obj).attrs
          if a.key not in EXCLUDE_REVIEW_FIELDS]):
    obj.review.status = all_models.Review.STATES.UNREVIEWED
    obj.review.agenda = "{user_email} made change in {target_slug}".format(
        user_email=obj.modified_by.display_name,
        target_slug=obj.slug,
    )


def set_review_msg(mapper, connecion, target):
  target.created_by = target.modified_by
  target.agenda = "{user_email} initiate review for {target_slug}".format(
      user_email=target.created_by.display_name,
      target_slug=target.instance.slug,
  )


def create_relationship(sender, obj=None, sources=None, objects=None):
  objects = objects or []
  if obj:
    objects.append(obj)
  for object in objects:
    if object:
      db.session.add(
          all_models.Relationship(source=object.instance, destination=object)
      )


def update_review_on_status_update(sender, obj=None, *args, **kwargs):
  if not db.inspect(obj).attrs["status"].history.has_changes():
    return
  if obj.status == all_models.Review.STATES.UNREVIEWED:
    obj.last_set_unreviewed_by = obj.modified_by
    obj.last_set_unreviewed_at = datetime.now()
  elif obj.status == all_models.Review.STATES.REVIEWED:
    obj.last_set_reviewed_by = obj.modified_by
    obj.last_set_reviewed_at = datetime.now()


def init_hook():
  """Init proposal signal handlers."""
  for model in all_models.all_models:
    if issubclass(model, review.Reviewable):
        signals.Restful.model_put.connect(
            update_review_status_on_reviewable_update,
            model,
            weak=False)
  event.listen(all_models.Review, "before_insert", set_review_msg)
  signals.Restful.collection_posted.connect(
      create_relationship,
      sender=review.Review,
      weak=False)
  signals.Restful.model_put.connect(
      update_review_on_status_update,
      sender=review.Review,
      weak=False)
