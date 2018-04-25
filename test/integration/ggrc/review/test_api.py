# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Base TestCase for proposal api."""

import contextlib
import itertools
import datetime

import ddt

from ggrc.models import all_models

from integration.ggrc import TestCase
from integration.ggrc.models import factories
from integration.ggrc.api_helper import Api


@ddt.ddt
class TestReviewApi(TestCase):
  """Base TestCase class proposal apip tests."""

  def setUp(self):
    super(TestReviewApi, self).setUp()
    self.api = Api()
    self.api.client.get("/login")

  def test_simple_get(self):
    review = factories.ReviewFactory()
    resp = self.api.get(all_models.Review, review.id)
    self.assert200(resp)
    self.assertIn("review", resp.json)
    self.assertEqual(all_models.Review.STATES.UNREVIEWED,
                     resp.json["review"]["status"])
    self.assertEqual(all_models.Review.NotificationContext.Types.EMAIL_TYPE,
                     resp.json["review"]["notification_type"])

  def test_collection_get(self):
    states = [all_models.Review.STATES.UNREVIEWED,
              all_models.Review.STATES.REVIEWED]
    notificaiton_types = [
        all_models.Review.NotificationContext.Types.EMAIL_TYPE,
        all_models.Review.NotificationContext.Types.ISSUE_TRACKER,
    ]
    reviews = {}
    with factories.single_commit():
      for state in states:
        for notificaiton_type in notificaiton_types:
          reviews[(state, notificaiton_type)] = factories.ReviewFactory()
    with factories.single_commit():
      for (state, notificaiton_type), review in reviews.iteritems():
        review.status = state
        review.notification_type = notificaiton_type
    resp = self.api.get_collection(all_models.Review,
                                   [r.id for r in reviews.values()])
    self.assert200(resp)
    self.assertIn("reviews_collection", resp.json)
    self.assertIn("reviews", resp.json["reviews_collection"])
    json_reviews = {i["id"]:i for i in
                    resp.json["reviews_collection"]["reviews"]}
    self.assertEqual(len(reviews), len(json_reviews))
    for (status, notification_type), review in reviews.iteritems():
      self.assertIn(review.id, json_reviews)
      json_review = json_reviews[review.id]
      self.assertEqual(status, json_review["status"])
      self.assertEqual(notification_type, json_review["notification_type"])

  @ddt.data(all_models.Review.STATES.UNREVIEWED,
            all_models.Review.STATES.REVIEWED)
  def test_update_reviewable(self, state):
    control = factories.ControlFactory()
    review = factories.ReviewFactory(status=state, instance=control)
    review_id = review.id
    instance = review.instance
    resp = self.api.put(
        instance,
        {"description": "some new description {}".format(instance.description)}
    )
    self.assert200(resp)
    review = all_models.Review.query.get(review_id)
    self.assertEqual(review.status, all_models.Review.STATES.UNREVIEWED)
    self.assertEqual("msg", review.agenda)

  @ddt.data(
      {
          "start_state": all_models.Review.STATES.UNREVIEWED,
          "update_state": all_models.Review.STATES.REVIEWED,
      },
      {
          "start_state": all_models.Review.STATES.REVIEWED,
          "update_state": all_models.Review.STATES.UNREVIEWED,
      },
      {
          "start_state": all_models.Review.STATES.UNREVIEWED,
          "update_state": all_models.Review.STATES.UNREVIEWED,
      },
      {
          "start_state": all_models.Review.STATES.REVIEWED,
          "update_state": all_models.Review.STATES.REVIEWED,
      }
  )
  @ddt.unpack
  def test_update_review(self, start_state, update_state):
    """Update review from {start_state} to {update_state}"""
    with factories.single_commit():
      control = factories.ControlFactory()
      person = factories.PersonFactory()
    person_id = person.id
    event_datetime = datetime.datetime.now() - datetime.timedelta(10)
    event_datetime.microsecond = 0
    review = factories.ReviewFactory(
        status=start_state,
        instance=control,
        last_set_reviewed_by=person,
        last_set_unreviewed_by=person,
        modified_by=person,
        last_set_reviewed_at=event_datetime,
        last_set_unreviewed_at=event_datetime,
    )
    review_id = review.id
    review = all_models.Review.query.get(review_id)
    self.assertEqual(start_state, review.status)
    self.assertEqual(person_id, review.last_set_reviewed_by_id)
    self.assertEqual(person_id, review.last_set_unreviewed_by_id)
    resp = self.api.put(review, {"status": update_state})
    self.assert200(resp)
    review = all_models.Review.query.get(review_id)
    self.assertEqual(update_state, review.status)
    self.assertEqual(1, review.modified_by_id)
    if start_state == update_state:
      self.assertEqual(person_id, review.last_set_reviewed_by_id)
      self.assertEqual(person_id, review.last_set_unreviewed_by_id)
      self.assertEqual(event_datetime, review.last_set_reviewed_at)
      self.assertEqual(event_datetime, review.last_set_unreviewed_at)
    elif update_state == all_models.Review.STATES.UNREVIEWED:
      self.assertEqual(person_id, review.last_set_reviewed_by_id)
      self.assertEqual(event_datetime, review.last_set_reviewed_at)
      self.assertNotEqual(person_id, review.last_set_unreviewed_by_id)
      self.assertNotEqual(event_datetime, review.last_set_unreviewed_at)
    else:
      self.assertNotEqual(person_id, review.last_set_reviewed_by_id)
      self.assertNotEqual(event_datetime, review.last_set_reviewed_at)
      self.assertEqual(person_id, review.last_set_unreviewed_by_id)
      self.assertEqual(event_datetime, review.last_set_unreviewed_at)



  @ddt.data(all_models.Review.STATES.UNREVIEWED,
            all_models.Review.STATES.REVIEWED)
  def test_create_review(self, state):
    control = factories.ControlFactory()
    control_id = control.id
    resp = self.api.post(
        all_models.Review,
        {
            "review": {
                "instance": {
                    "type": control.type,
                    "id": control.id,
                },
                "context": None,
                "notification_type": "email",
                "status": state,
            },
        },
    )
    self.assertEqual(201, resp.status_code)
    review_id = resp.json["review"]["id"]
    review = all_models.Review.query.get(review_id)
    self.assertEqual(state, review.status)
    self.assertEqual(control.type, review.instance_type)
    self.assertEqual(control_id, review.instance_id)
    self.assertEqual(
        1,
        all_models.Relationship.query.filter(
            all_models.Relationship.source_id == review.id,
            all_models.Relationship.source_type == review.type,
            all_models.Relationship.destination_id == control_id,
            all_models.Relationship.destination_type == control.type,
        ).union(
            all_models.Relationship.query.filter(
                all_models.Relationship.destination_id == review.id,
                all_models.Relationship.destination_type == review.type,
                all_models.Relationship.source_id == control_id,
                all_models.Relationship.source_type == control.type,
            )
        ).count()
    )

  @ddt.data(all_models.Review.STATES.UNREVIEWED,
            all_models.Review.STATES.REVIEWED)
  def test_delete_review(self, state):
    control = factories.ControlFactory()
    review = factories.ReviewFactory(status=all_models.Review.STATES.REVIEWED,
                                     instance=control)
    relationship = factories.RelationshipFactory(source=control,
                                                 destination=review)
    review_id = review.id
    relationship_id = relationship.id
    resp = self.api.delete(review)
    self.assert200(resp)
    review = all_models.Review.query.get(review_id)
    relationship = all_models.Relationship.query.get(relationship_id)
    self.assertIsNone(review)
    self.assertIsNone(relationship)



