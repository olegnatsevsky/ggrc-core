# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Base TestCase for automatic review status update."""

import ddt

from ggrc.models import all_models

from integration.ggrc import TestCase
from integration.ggrc.models import factories

from integration.ggrc.api_helper import Api


@ddt.ddt
class TestReviewStatusUpdate(TestCase):
  """Base TestCase class automatic review status update."""

  def setUp(self):
    super(TestReviewStatusUpdate, self).setUp()
    self.api = Api()
    self.api.client.get("/login")

  @ddt.data(
        ("title", "new title"),
        ("description", "new description"),
        ("test_plan", "new test_plan"),
        ("notes", "new notes"),
        ("fraud_related", 1),
        ("key_control", 1),
        ("start_date", "2020-01-01"),
        ("status", "Active"),
        ("kind", lambda: {
          "id": all_models.Option.query.filter_by(role="control_kind",
                                                  title="Detective").one().id,
          "type": "Option"
        }),
        ("means", lambda: {
          "id": all_models.Option.query.filter_by(role="control_means",
                                                  title="Technical").one().id,
          "type": "Option"
        }),
        ("verify_frequency", lambda: {
          "id": all_models.Option.query.filter_by(role="verify_frequency",
                                                  title="Daily").one().id,
          "type": "Option"
        })

    )
  @ddt.unpack
  def test_reviewable_attributes(self, attr_to_modify, new_value):
    """If attribute '{0}' modified move review to Unreviewed state"""
    with factories.single_commit():
      control = factories.ControlFactory()
      review = factories.ReviewFactory(status=all_models.Review.STATES.REVIEWED,
                                       reviewable=control)
    review_id = review.id
    reviewable = review.reviewable

    review = all_models.Review.query.get(review_id)

    self.assertEqual(review.status, all_models.Review.STATES.REVIEWED)

    self.api.modify_object(reviewable, {
      attr_to_modify: new_value() if callable(new_value) else new_value
    })

    review = all_models.Review.query.get(review_id)
    self.assertEqual(review.status, all_models.Review.STATES.UNREVIEWED)
