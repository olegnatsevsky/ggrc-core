# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Review RBAC Factory."""

from ggrc.models import all_models
from integration.ggrc.models import factories

from integration.ggrc.access_control.rbac_factories import universal_factory
from integration.ggrc.models.factories import get_model_factory


class MappedReviewRBACFactory(universal_factory.UniversalRBACFactory):
  def __init__(self, user_id, acr, parent=None, role_at_review=False):
    self.parent = None
    self.parent_id = None
    self.parent_name = None
    self.role_at_review = role_at_review
    self.reviewer_acr = all_models.AccessControlRole.query.filter_by(
        name="Reviewer",
        object_type="Review",
    ).one()
    self.reviewer_acr_id = self.reviewer_acr.id
    self.review_id = None
    super(MappedReviewRBACFactory, self).__init__(user_id, acr, parent)

  def setup_models(self, parent_name):
    """Setup Review, Reviewer"""
    with factories.single_commit():
      self.parent = get_model_factory(parent_name)()
      self.parent_id = self.parent.id
      self.parent_name = parent_name
      review = factories.ReviewFactory(reviewable=self.parent)
      self.review_id = review.id
      factories.RelationshipFactory(source=self.parent, destination=review)
      if self.role_at_review:
        self.assign_person(review, self.acr, self.user_id)
      else:
        self.assign_person(self.parent, self.acr, self.user_id)

  def create_review(self):
    """Create new Review object."""
    result = self.api.post(all_models.Review, {
        "review": {
            "access_control_list": [{
                "ac_role_id": self.reviewer_acr_id,
                "person": {"id": self.user_id, "type": "Person"}
            }],
            "reviewable": {
                "type": self.parent_name,
                "id": self.parent_id,
            },
            "context": None,
            "notification_type": "email",
            "status": all_models.Review.STATES.UNREVIEWED,
        },
    })
    return result

  def read_review(self):
    """Read existing Review object."""
    res = self.api.get(all_models.Review, self.review_id)
    return res

  def update_review(self):
    """Update status of existing Review object."""
    review = all_models.Review.query.get(self.review_id)
    return self.api.put(review, {"status": all_models.Review.STATES.REVIEWED})

  def delete_review(self):
    """Delete Review object."""
    review = all_models.Review.query.get(self.review_id)
    return self.api.delete(review)
