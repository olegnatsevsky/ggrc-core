# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Base TestCase for automatic review status update."""

import ddt

from ggrc.models import all_models

from integration.ggrc import TestCase, generator
from integration.ggrc.models import factories

from integration.ggrc.api_helper import Api


def build_related_object_data(role, title):
  return {
      "id": all_models.Option.query.filter_by(role=role, title=title).one().id,
      "type": "Option"
  }


def get_kind_data():
  return build_related_object_data("control_kind", "Detective")


def get_mean_data():
  return build_related_object_data("control_means", "Technical")


def get_verify_frequency_data():
  return build_related_object_data("verify_frequency", "Daily")


def get_assertions_data():
  return [
      {
          "id":
          all_models.CategoryBase.query.filter_by(
              name="Availability", type="ControlAssertion"
          ).one().id
      }
  ]


def get_categories_data():
  return [
      {
          "id":
          all_models.CategoryBase.query.filter_by(
              name="Data Centers", type="ControlCategory"
          ).one().id
      }
  ]


@ddt.ddt
class TestReviewStatusUpdate(TestCase):
  """Base TestCase class automatic review status update."""

  def setUp(self):
    super(TestReviewStatusUpdate, self).setUp()
    self.api = Api()
    self.api.client.get("/login")
    self.obj_gen = generator.ObjectGenerator()

  @ddt.data(
      ("title", "new title"),
      ("description", "new description"),
      ("test_plan", "new test_plan"),
      ("notes", "new notes"),
      ("fraud_related", 1),
      ("key_control", 1),
      ("start_date", "2020-01-01"),
      ("status", "Active"),
      ("kind", get_kind_data),
      ("means", get_mean_data),
      ("verify_frequency", get_verify_frequency_data),
      ("assertions", get_assertions_data),
      ("categories", get_categories_data),
  )
  @ddt.unpack
  def test_reviewable_attributes(self, attr_to_modify, new_value):
    """If attribute '{0}' modified move review to Unreviewed state"""
    with factories.single_commit():
      control = factories.ControlFactory()
      review = factories.ReviewFactory(
          status=all_models.Review.STATES.REVIEWED, reviewable=control
      )
    review_id = review.id
    reviewable = review.reviewable

    self.api.modify_object(
        reviewable,
        {attr_to_modify: new_value() if callable(new_value) else new_value}
    )

    review = all_models.Review.query.get(review_id)
    self.assertEqual(review.status, all_models.Review.STATES.UNREVIEWED)

  def test_gca(self):
    """if GCA of reviewable is changed review -> unreviewed"""
    with factories.single_commit():
      ca_factory = factories.CustomAttributeDefinitionFactory
      gca = ca_factory(
          definition_type="control",
          title="rich_test_gca",
          attribute_type="Rich Text"
      )
      control = factories.ControlFactory()
      review = factories.ReviewFactory(
          status=all_models.Review.STATES.REVIEWED, reviewable=control
      )
    review_id = review.id
    reviewable = review.reviewable

    review = all_models.Review.query.get(review_id)

    self.assertEqual(review.status, all_models.Review.STATES.REVIEWED)

    self.api.modify_object(
        reviewable, {
            "custom_attribute_values":
            [{
                "custom_attribute_id": gca.id,
                "attribute_value": "new_value",
            }],
        }
    )

    review = all_models.Review.query.get(review_id)
    self.assertEqual(review.status, all_models.Review.STATES.UNREVIEWED)

  def test_reference_url(self):
    """If reference url is updated state should not updated"""
    with factories.single_commit():
      control = factories.ControlFactory()
      doc = factories.DocumentReferenceUrlFactory(
          title="Simple title",
          link="some_url.com",
          description="mega description",
          parent_obj={
              "id": control.id,
              "type": "Control"
          }
      )
      review = factories.ReviewFactory(
          status=all_models.Review.STATES.REVIEWED, reviewable=control
      )
    review_id = review.id

    self.api.modify_object(doc, {"link": "new_link.com"})
    review = all_models.Review.query.get(review_id)
    self.assertEqual(review.status, all_models.Review.STATES.REVIEWED)

  def test_acl_roles(self):
    """Update of reviewable ACL shouldn't change review status"""
    with factories.single_commit():
      control = factories.ControlFactory()
      review = factories.ReviewFactory(
          status=all_models.Review.STATES.REVIEWED, reviewable=control
      )
    review_id = review.id

    ac_role_id = all_models.AccessControlRole.query.filter_by(
        name="Primary Contacts", object_type="Control"
    ).one().id

    user_id = all_models.Person.query.filter_by(
        email="user@example.com"
    ).one().id

    self.api.modify_object(
        control, {
            "access_control_list": [{
                "ac_role_id": ac_role_id,
                "person": {
                    "id": user_id
                },
            }],
        }
    )
    review = all_models.Review.query.get(review_id)
    self.assertEqual(review.status, all_models.Review.STATES.REVIEWED)

  def test_comments(self):
    """Add comment to reviewable shouldn't update review state"""
    with factories.single_commit():
      control = factories.ControlFactory()
      review = factories.ReviewFactory(
          status=all_models.Review.STATES.REVIEWED, reviewable=control
      )
    review_id = review.id

    self.obj_gen.generate_comment(
        control, "Verifiers", "some comment", send_notification="false"
    )

    review = all_models.Review.query.get(review_id)
    self.assertEqual(review.status, all_models.Review.STATES.REVIEWED)

  def test_mapping_non_snapshotable(self):
    """Map non-snapshotable shouldn't change review status"""
    with factories.single_commit():
      control = factories.ControlFactory()
      review = factories.ReviewFactory(
          status=all_models.Review.STATES.REVIEWED, reviewable=control
      )
      review_id = review.id

    factories.RelationshipFactory(
        source=control, destination=factories.IssueFactory()
    )

    review = all_models.Review.query.get(review_id)
    self.assertEqual(review.status, all_models.Review.STATES.REVIEWED)

  @ddt.data(
      "Standard",
      "Regulation",
      "Requirement",
      "Objective",
      "Control",
      "Product",
      "Contract",
      "Policy",
      "Risk",
      "Threat",
  )
  def test_map_snapshotable(self, snapshotable):
    """Map '{}' should change review status"""
    with factories.single_commit():
      control = factories.ControlFactory()
      review = factories.ReviewFactory(
          status=all_models.Review.STATES.REVIEWED, reviewable=control
      )
      review_id = review.id

    self.obj_gen.generate_relationship(
        source=control,
        destination=factories.get_model_factory(snapshotable)(),
        context=None,
    )

    review = all_models.Review.query.get(review_id)
    self.assertEqual(review.status, all_models.Review.STATES.UNREVIEWED)

  def test_unmap_snapshotable(self):
    """Unmap snapshotable should change review status"""
    with factories.single_commit():
      control = factories.ControlFactory()
      review = factories.ReviewFactory(reviewable=control)
      review_id = review.id

    _, rel = self.obj_gen.generate_relationship(
        source=control,
        destination=factories.ProductFactory(),
        context=None,
    )

    review = all_models.Review.query.get(review_id)
    resp = self.api.modify_object(
        review, {"status": all_models.Review.STATES.REVIEWED}
    )
    self.assert200(resp)

    resp = self.api.delete(rel)
    self.assert200(resp)
    review = all_models.Review.query.get(review_id)
    self.assertEqual(review.status, all_models.Review.STATES.UNREVIEWED)

  @ddt.data(
      "Assessment",
      "Issue",
      "Program",
      "Project",
      "Audit",
      "RiskAssessment",
      "AssessmentTemplate",
      "Person",
  )
  def test_map_nonsnapshotable(self, nonsnapshotable):
    """Map '{}' shouldn't change review status"""
    with factories.single_commit():
      control = factories.ControlFactory()
      review = factories.ReviewFactory(
          status=all_models.Review.STATES.REVIEWED, reviewable=control
      )
      review_id = review.id

    review = all_models.Review.query.get(review_id)

    self.assertEqual(review.status, all_models.Review.STATES.REVIEWED)

    self.obj_gen.generate_relationship(
        source=control,
        destination=factories.get_model_factory(nonsnapshotable)(),
        context=None,
    )

    review = all_models.Review.query.get(review_id)
    self.assertEqual(review.status, all_models.Review.STATES.REVIEWED)

  def test_unmap_nonsnapshotable(self):
    """Unmap nonsnapshotable shouldn't change review status"""
    with factories.single_commit():
      control = factories.ControlFactory()
      review = factories.ReviewFactory(reviewable=control)
      review_id = review.id

    _, rel = self.obj_gen.generate_relationship(
        source=control,
        destination=factories.ProgramFactory(),
        context=None,
    )

    review = all_models.Review.query.get(review_id)
    resp = self.api.modify_object(
        review, {"status": all_models.Review.STATES.REVIEWED}
    )
    self.assert200(resp)
    review = all_models.Review.query.get(review_id)
    self.assertEqual(review.status, all_models.Review.STATES.REVIEWED)

    resp = self.api.delete(rel)
    self.assert200(resp)
    review = all_models.Review.query.get(review_id)
    self.assertEqual(review.status, all_models.Review.STATES.REVIEWED)

  @unittest.skip("Skipped until control not Reviewable")
  def test_proposal_apply(self):
    """Reviewable object changed via proposal -> review.state-> UNREVIEWED"""
    with factories.single_commit():
      control = factories.ControlFactory()
      review = factories.ReviewFactory(
          status=all_models.Review.STATES.REVIEWED, reviewable=control
      )
      review_id = review.id

      proposal_content = {
          "fields": {
              "title": "new title"
          },
      }
      proposal = factories.ProposalFactory(instance=control,
                                           content=proposal_content,
                                           agenda="agenda content")
    self.api.modify_object(proposal, {
        "status": proposal.STATES.APPLIED
    })

    review = all_models.Review.query.get(review_id)
    self.assertEqual(review.status, all_models.Review.STATES.UNREVIEWED)
