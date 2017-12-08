# Copyright (C) 2017 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Integration test for AutoStatusChangeable mixin"""

import ddt

from ggrc import models
from ggrc.access_control.role import get_custom_roles_for

from integration.ggrc import api_helper
from integration.ggrc import generator
from integration.ggrc.models import factories
from integration.ggrc.models.test_assessment import TestAssessmentBase


@ddt.ddt
class TestMixinAutoStatusChangeable(TestAssessmentBase):

  """Test case for AutoStatusChangeable mixin"""

  # pylint: disable=invalid-name

  def setUp(self):
    super(TestMixinAutoStatusChangeable, self).setUp()
    self.client.get("/login")
    self.api_helper = api_helper.Api()
    self.objgen = generator.ObjectGenerator()

  def test_open_to_in_progress_first_class_edit(self):
    """Test first class edit - it should move Assessment to Progress state"""
    assessment = self.create_assessment()

    self.assertEqual(assessment.status, models.Assessment.START_STATE)

    self.api_helper.modify_object(assessment, {
        "title": assessment.title + " modified, change #1"
    })
    assessment = self.refresh_object(assessment)
    self.assertEqual(assessment.status, models.Assessment.PROGRESS_STATE)

  @ddt.data("DONE_STATE", "START_STATE")
  def test_changing_assignees_should_not_change_status(self, test_state):
    """Adding/chaning/removing assignees shouldn't change status

    Test assessment in FINAL_STATE should not get to PROGRESS_STATE on
    assignee edit.
    """
    people = [
        ("creator@example.com", "Creators"),
        ("assessor_1@example.com", "Assignees"),
        ("assessor_2@example.com", "Assignees"),
    ]

    assessment = self.create_assessment(people)
    assessment = self.refresh_object(assessment)
    assessment = self.change_status(assessment,
                                    getattr(assessment, test_state))
    self.assertEqual(assessment.status,
                     getattr(models.Assessment, test_state))
    self.modify_assignee(assessment,
                         "creator@example.com",
                         ["Creators", "Assignees"])
    assessment = self.refresh_object(assessment)
    self.assertEqual(assessment.status,
                     getattr(models.Assessment, test_state))
    new_assessors = [("assessor_3_added_later@example.com", "Verifiers")]
    self.create_assignees_restful(assessment, new_assessors)
    assessment = self.refresh_object(assessment)
    self.assertEqual(assessment.status,
                     getattr(models.Assessment, test_state))
    self.delete_assignee(assessment, "assessor_1@example.com")
    assessment = self.refresh_object(assessment)
    self.assertEqual(assessment.status,
                     getattr(models.Assessment, test_state))

  def test_assessment_verifiers_full_cycle_first_class_edit(self):
    """Test Assessment with verifiers full flow

    Test moving from START_STATE to PROGRESS_STATE to FINAL_STATE and back to
    PROGRESS_STATE on edit.
    """
    assessment = self.create_assessment()

    self.assertEqual(assessment.status,
                     models.Assessment.START_STATE)

    assessment = self.refresh_object(assessment)

    self.api_helper.modify_object(assessment, {
        "title": assessment.title + " modified, change #1"
    })

    assessment = self.refresh_object(assessment)

    assessment = self.change_status(assessment, assessment.DONE_STATE)

    self.assertEqual(assessment.title.endswith("modified, change #1"),
                     True)

    self.assertEqual(assessment.status,
                     models.Assessment.DONE_STATE)

    self.api_helper.modify_object(assessment, {
        "title": assessment.title + " modified, change #2"
    })
    assessment = self.refresh_object(assessment)
    self.assertEqual(assessment.title.endswith("modified, change #2"),
                     True)
    self.assertEqual(assessment.status,
                     models.Assessment.PROGRESS_STATE)

    assessment = self.change_status(assessment,
                                    assessment.VERIFIED_STATE,
                                    assessment.FINAL_STATE)

    self.assertEqual(assessment.status, assessment.FINAL_STATE)
    self.assertEqual(assessment.verified, True)

    self.api_helper.modify_object(assessment, {
        "title": assessment.title + "modified, change #3"
    })
    assessment = self.refresh_object(assessment)
    self.assertEqual(assessment.title.endswith("modified, change #3"),
                     True)
    self.assertEqual(assessment.status,
                     models.Assessment.PROGRESS_STATE)

  def test_modifying_person_custom_attribute_changes_status(self):
    """Test that changing a Person CA changes the status to in progress."""
    person_id = models.Person.query.first().id
    _, another_person = self.objgen.generate_person()

    # define a Custom Attribute of type Person...
    _, ca_def = self.objgen.generate_custom_attribute(
        definition_type="assessment",
        attribute_type="Map:Person",
        title="best employee")

    # create assessment with a Person Custom Attribute set, make sure the
    # state is set to final
    assessment = self.create_simple_assessment()

    custom_attribute_values = [{
        "custom_attribute_id": ca_def.id,
        "attribute_value": "Person:" + str(person_id),
    }]
    self.api_helper.modify_object(assessment, {
        "custom_attribute_values": custom_attribute_values
    })

    assessment = self.change_status(assessment, assessment.FINAL_STATE)
    assessment = self.refresh_object(assessment)

    # now change the Person CA and check what happens with the status
    custom_attribute_values = [{
        "custom_attribute_id": ca_def.id,
        "attribute_value": "Person:" + str(another_person.id),  # make a change
    }]
    self.api_helper.modify_object(assessment, {
        "custom_attribute_values": custom_attribute_values
    })

    assessment = self.refresh_object(assessment)
    self.assertEqual(assessment.status, models.Assessment.PROGRESS_STATE)

    # perform the same test for the "in review" state
    assessment = self.change_status(assessment, assessment.DONE_STATE)
    assessment = self.refresh_object(assessment)

    custom_attribute_values = [{
        "custom_attribute_id": ca_def.id,
        "attribute_value": "Person:" + str(person_id),  # make a change
    }]
    self.api_helper.modify_object(assessment, {
        "custom_attribute_values": custom_attribute_values
    })

    assessment = self.refresh_object(assessment)
    self.assertEqual(assessment.status, models.Assessment.PROGRESS_STATE)

  def create_assignees_restful(self, obj, persons):
    """Add assignees via RESTful API instead of directly via backend.

    Used for addind assignees after object has already been created.

    Args:
      obj: Assignable object.
      persons: [("(string) email", "Assignee roles"), ...] A list of people
        and their roles
    Returns:
      List of relationship.
    """

    relationships = []
    for person, roles in persons:
      person = factories.PersonFactory(email=person)

      attrs = {
          "AssigneeType": roles,
      }
      response, relationship = self.objgen.generate_relationship(
          person, obj, context=obj.context, attrs=attrs)
      self.assertEqual(response.status_code, 201)

      relationships += [relationship]
    return relationships

  def modify_assignee(self, obj, email, new_roles):
    """Modfiy assignee type.

    Args:
      obj: Object
      email: Person's email
      new_role: New roles for AssigneeType
    """
    person = models.Person.query.filter_by(email=email).first()
    ac_roles = {
        acr_name: acr_id
        for acr_id, acr_name in get_custom_roles_for(obj.type).items()
    }
    self.api_helper.modify_object(obj, {
        "access_control_list": [{
            "ac_role_id": ac_roles[role],
            "person": {
                "id": person.id
            },
        } for role in new_roles]
    })

  def delete_assignee(self, obj, email):
    """Deletes user-object relationship user when no more assignee roles.

    This operation is equal to deleting user from a role when that is his only
    role left on the object.

    Args:
      obj: object
      email: assignee's email
    """
    self.modify_assignee(obj, email, [])

  def create_assessment(self, people=None):
    """Create default assessment with some default assignees in all roles.
    Args:
      people: List of tuples with email address and their assignee roles for
              Assessments.
    Returns:
      Assessment object.
    """
    assessment = factories.AssessmentFactory()
    context = factories.ContextFactory(related_object=assessment)
    assessment.context = context

    if not people:
      people = [
          ("creator@example.com", "Creators"),
          ("assessor_1@example.com", "Assignees"),
          ("assessor_2@example.com", "Assignees"),
          ("verifier_1@example.com", "Verifiers"),
          ("verifier_2@example.com", "Verifiers"),
      ]

    defined_assessors = len([1 for _, role in people
                             if "Assignees" in role])
    defined_creators = len([1 for _, role in people
                            if "Creators" in role])
    defined_verifiers = len([1 for _, role in people
                             if "Verifiers" in role])

    assignee_roles = self.create_assignees(assessment, people)

    creators = [assignee for assignee, roles in assignee_roles
                if "Creators" in roles]
    assignees = [assignee for assignee, roles in assignee_roles
                 if "Assignees" in roles]
    verifiers = [assignee for assignee, roles in assignee_roles
                 if "Verifiers" in roles]

    self.assertEqual(len(creators), defined_creators)
    self.assertEqual(len(assignees), defined_assessors)
    self.assertEqual(len(verifiers), defined_verifiers)
    return assessment

  def change_status(self, obj, status,
                    expected_status=None, check_verified=False):
    """Change status of an object."""
    self.api_helper.modify_object(obj, {
        "status": status
    })
    obj = self.refresh_object(obj)
    if expected_status:
      self.assertEqual(obj.status, expected_status)
    else:
      self.assertEqual(obj.status, status)

    if check_verified:
      self.assertEqual(obj.verified, True)
    return obj

  def create_simple_assessment(self):
    """Create simple assessment with some assignees and in FINAL state."""
    people = [
        ("creator@example.com", "Creators"),
        ("assessor_1@example.com", "Assignees"),
        ("assessor_2@example.com", "Assignees"),
    ]

    assessment = self.create_assessment(people)
    assessment = self.refresh_object(assessment)

    self.api_helper.modify_object(assessment, {
        "title": assessment.title + " modified, change #1"
    })

    assessment = self.refresh_object(assessment)

    assessment = self.change_status(assessment, assessment.FINAL_STATE)

    assessment = self.refresh_object(assessment)

    self.assertEqual(assessment.status,
                     models.Assessment.FINAL_STATE)
    return assessment

  def create_assessment_in_ready_to_review(self):
    """Create an assessment with some assignees in READY TO REVIEW state."""
    people = [
        ("creator@example.com", "Creators"),
        ("assessor_1@example.com", "Assignees"),
        ("assessor_2@example.com", "Assignees"),
    ]

    assessment = self.create_assessment(people)
    assessment = self.refresh_object(assessment)

    self.api_helper.modify_object(assessment, {
        "title": assessment.title + " modified, change #1"
    })

    assessment = self.refresh_object(assessment)
    assessment = self.change_status(assessment, assessment.DONE_STATE)
    assessment = self.refresh_object(assessment)

    self.assertEqual(assessment.status,
                     models.Assessment.DONE_STATE)
    return assessment

  def test_asmt_with_mandatory_lca_to_deprecated_state(self):
    """Test new Assessment with not filled mandatory LCA could be Deprecated"""
    # pylint: disable=attribute-defined-outside-init
    with factories.single_commit():
      self.audit = factories.AuditFactory()
      self.control = factories.ControlFactory(test_plan="Control Test Plan")
      self.snapshot = self._create_snapshots(self.audit, [self.control])[0]

      template = factories.AssessmentTemplateFactory(
          test_plan_procedure=False,
          procedure_description="Assessment Template Test Plan"
      )
      custom_attribute_definition = {
          "definition_type": "assessment_template",
          "definition_id": template.id,
          "title": "test checkbox",
          "attribute_type": "Checkbox",
          "multi_choice_options": "test checkbox label",
          "mandatory": True,
      }
      factories.CustomAttributeDefinitionFactory(**custom_attribute_definition)

    response = self.assessment_post(template)

    self.assertEqual(response.json["assessment"]["status"],
                     models.Assessment.START_STATE)
    asmt = models.Assessment.query.get(response.json["assessment"]["id"])
    asmt = self.change_status(asmt, models.Assessment.DEPRECATED)
    asmt = self.refresh_object(asmt)
    self.assertEqual(asmt.status, models.Assessment.DEPRECATED)
