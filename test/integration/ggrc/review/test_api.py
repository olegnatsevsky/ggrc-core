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
    #TODO add issuetracker data
    with factories.single_commit():
      control = factories.ControlFactory()
      review = factories.ReviewFactory(
          email_message="test email message",
          notification_type="email",
          reviewable=control,
          status=all_models.Review.STATES.UNREVIEWED
      )
    resp = self.api.get(all_models.Review, review.id)
    self.assert200(resp)
    self.assertIn("review", resp.json)
    self.assertEqual(all_models.Review.STATES.UNREVIEWED,
                     resp.json["review"]["status"])
    self.assertEqual(all_models.Review.NotificationContext.Types.EMAIL_TYPE,
                     resp.json["review"]["notification_type"])
    self.assertEqual("test email message",
                     resp.json["review"]["email_message"])

  def test_collection_get(self):
    """Test simple collection get"""
    with factories.single_commit():
      review1 = factories.ReviewFactory(
         status=all_models.Review.STATES.UNREVIEWED
      )
      review2 = factories.ReviewFactory(
        status=all_models.Review.STATES.REVIEWED
      )

    resp = self.api.get_collection(all_models.Review,
                                   [review1.id, review2.id])
    self.assert200(resp)
    self.assertIn("reviews_collection", resp.json)
    self.assertIn("reviews", resp.json["reviews_collection"])
    self.assertEquals(2, len(resp.json["reviews_collection"]["reviews"]))

  def test_create_review(self):
    """Create review via API, check that single relationship is created"""
    control = factories.ControlFactory()
    control_id = control.id
    resp = self.api.post(
        all_models.Review,
        {
            "review": {
                "reviewable": {
                    "type": control.type,
                    "id": control.id,
                },
                "context": None,
                "notification_type": "email",
                "status": all_models.Review.STATES.UNREVIEWED,
            },
        },
    )
    self.assertEqual(201, resp.status_code)
    review_id = resp.json["review"]["id"]
    review = all_models.Review.query.get(review_id)
    self.assertEqual(all_models.Review.STATES.UNREVIEWED, review.status)
    self.assertEqual(control.type, review.reviewable_type)
    self.assertEqual(control_id, review.reviewable_id)

    control_review_rel_count = all_models.Relationship.query.filter(
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
    self.assertEqual(1, control_review_rel_count)

  def test_delete_review(self):
    """Test delete review via API"""
    control = factories.ControlFactory()
    review = factories.ReviewFactory(reviewable=control)
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

  @ddt.data(all_models.Review.STATES.UNREVIEWED,
            all_models.Review.STATES.REVIEWED)
  def test_update_reviewable(self, state):
    """Test change of review description reset state to unreviewed"""
    #TODO move this test to auto status update
    with factories.single_commit():
      control = factories.ControlFactory()
      review = factories.ReviewFactory(status=state, reviewable=control)
      review_id = review.id
      reviewable = review.reviewable

    resp = self.api.put(
        reviewable,
        {
            "description":
            "some new description {}".format(reviewable.description)
        }
    )
    self.assert200(resp)
    review = all_models.Review.query.get(review_id)
    self.assertEqual(review.status, all_models.Review.STATES.UNREVIEWED)
