# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Base TestCase for proposal api."""

import contextlib
import itertools

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

  @ddt.data(all_models.Review.STATES.UNREVIEWED,
            all_models.Review.STATES.REVIEWED)
  def test_update_review(self, state):
    control = factories.ControlFactory()
    review = factories.ReviewFactory(status=all_models.Review.STATES.REVIEWED,
                                     instance=control)
    review_id = review.id
    review = all_models.Review.query.get(review_id)
    self.assertEqual(all_models.Review.STATES.REVIEWED, review.status)
    resp = self.api.put(review, {"status": state})
    self.assert200(resp)
    review = all_models.Review.query.get(review_id)
    self.assertEqual(state, review.status)

  @ddt.data(all_models.Review.STATES.UNREVIEWED,
            all_models.Review.STATES.REVIEWED)
  def test_create_review(self, state):
    control = factories.ControlFactory()
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
