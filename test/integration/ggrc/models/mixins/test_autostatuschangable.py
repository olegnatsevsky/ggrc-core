# Copyright (C) 2017 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Integration test for AutoStatusChangeable mixin"""

import ddt

from ggrc import db
from ggrc import models
from ggrc.access_control.role import get_custom_roles_for
from integration.ggrc import Api
from integration.ggrc import api_helper
from integration.ggrc import generator
from integration.ggrc import TestCase
from integration.ggrc.models import factories


class TestMixinAutoStatusChangeableBase(TestCase):
  """Base Test case for AutoStatusChangeable mixin"""

  def setUp(self):
    super(TestMixinAutoStatusChangeableBase, self).setUp()
    self.client.get("/login")
    self.api_helper = api_helper.Api()
    self.api = Api()
    self.objgen = generator.ObjectGenerator()

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

    self.assertEqual(assessment.status, models.Assessment.FINAL_STATE)
    return assessment


@ddt.ddt
class TestFirstClassAttributes(TestMixinAutoStatusChangeableBase):
  """Test case for AutoStatusChangeable first class attributes handlers"""
  # pylint: disable=invalid-name

  @ddt.data(models.Assessment.DONE_STATE,
            models.Assessment.FINAL_STATE,
            models.Assessment.PROGRESS_STATE,
            models.Assessment.REWORK_NEEDED
            )
  def test_update_label_not_change_status(self, from_status):
    """Change field label should not change status"""
    # This test should fail when new Label implementation will be merged

    # Arrange
    with factories.single_commit():
      assessment = factories.AssessmentFactory(status=from_status)

    # Act
    self.api_helper.modify_object(assessment, {
        'label': 'Followup'
    })
    assessment = self.refresh_object(assessment)
    # Assert
    self.assertEqual(from_status, assessment.status)

  @ddt.data(
      ('title', 'new title', models.Assessment.DONE_STATE,),
      ('title', 'new title', models.Assessment.FINAL_STATE),
      ('test_plan', 'test_plan v2', models.Assessment.DONE_STATE),
      ('test_plan', 'test_plan v2', models.Assessment.FINAL_STATE),
      ('notes', 'new note', models.Assessment.DONE_STATE),
      ('notes', 'new note', models.Assessment.FINAL_STATE),
      ('description', 'some description', models.Assessment.DONE_STATE),
      ('description', 'some description', models.Assessment.FINAL_STATE),
      ('slug', 'some code', models.Assessment.DONE_STATE),
      ('slug', 'some code', models.Assessment.FINAL_STATE),
      ('start_date', '2020-01-01', models.Assessment.DONE_STATE),
      ('start_date', '2020-01-01', models.Assessment.FINAL_STATE),
      ('design', 'Effective', models.Assessment.DONE_STATE),
      ('design', 'Effective', models.Assessment.FINAL_STATE),
      ('operationally', 'Effective', models.Assessment.DONE_STATE),
      ('operationally', 'Effective', models.Assessment.FINAL_STATE),
      ('assessment_type', 'Risk', models.Assessment.DONE_STATE),
      ('assessment_type', 'Risk', models.Assessment.FINAL_STATE),
  )
  @ddt.unpack
  def test_update_field_change_status(self, field_name, new_value,
                                      from_status):
    """When assessment in status '{2}' and field '{0}' updated ->
    status should be changed to 'In Progress'"""
    # Arrange
    with factories.single_commit():
      assessment = factories.AssessmentFactory(status=from_status)
    expected_status = models.Assessment.PROGRESS_STATE

    # Act
    self.api_helper.modify_object(assessment, {
        field_name: new_value
    })
    assessment = self.refresh_object(assessment)
    # Assert
    self.assertEqual(expected_status, assessment.status)

  @ddt.data(
      ('title', 'new title', models.Assessment.START_STATE),
      ('title', 'new title', models.Assessment.REWORK_NEEDED),
      ('test_plan', 'test_plan v2', models.Assessment.START_STATE),
      ('test_plan', 'test_plan v2', models.Assessment.REWORK_NEEDED),
      ('notes', 'new note', models.Assessment.START_STATE),
      ('notes', 'new note', models.Assessment.REWORK_NEEDED),
      ('description', 'some description', models.Assessment.START_STATE),
      ('description', 'some description', models.Assessment.REWORK_NEEDED),
      ('slug', 'some code', models.Assessment.START_STATE),
      ('slug', 'some code', models.Assessment.REWORK_NEEDED),
      ('start_date', '2020-01-01', models.Assessment.START_STATE),
      ('start_date', '2020-01-01', models.Assessment.REWORK_NEEDED),
      ('design', 'Effective', models.Assessment.START_STATE),
      ('design', 'Effective', models.Assessment.REWORK_NEEDED),
      ('operationally', 'Effective', models.Assessment.START_STATE),
      ('operationally', 'Effective', models.Assessment.REWORK_NEEDED),
      ('assessment_type', 'Risk', models.Assessment.START_STATE),
      ('assessment_type', 'Risk', models.Assessment.REWORK_NEEDED),
  )
  @ddt.unpack
  def test_update_field_not_change_status(self, field_name, new_value,
                                          from_status):
    """When assessment in status '{2}' and field '{0}' updated ->
     status should NOT be changed"""
    # Arrange
    with factories.single_commit():
      assessment = factories.AssessmentFactory(status=from_status)
    # Act
    self.api_helper.modify_object(assessment, {
        field_name: new_value
    })
    assessment = self.refresh_object(assessment)
    # Assert
    self.assertEqual(from_status, assessment.status)


@ddt.ddt
class TestSnapshots(TestMixinAutoStatusChangeableBase):
  """Test case for AutoStatusChangeable mapping/unmapping snapshots handlers"""
  # pylint: disable=invalid-name

  @ddt.data(
      (models.Assessment.DONE_STATE, models.Assessment.PROGRESS_STATE),
      (models.Assessment.FINAL_STATE, models.Assessment.PROGRESS_STATE),
      (models.Assessment.START_STATE, models.Assessment.START_STATE),
      (models.Assessment.REWORK_NEEDED, models.Assessment.REWORK_NEEDED),
  )
  @ddt.unpack
  def test_mapping_snapshot_type_status_check(self, from_status,
                                              expected_status):
    """When assessment in status '{0}' and Map Snapshot(type=assessment type)->
    status should be changed to '{1}'"""
    # Arrange
    with factories.single_commit():
      audit = factories.AuditFactory()
      assessment = factories.AssessmentFactory(audit=audit, status=from_status)
      factories.RelationshipFactory(source=audit, destination=assessment)
      control = factories.ControlFactory(title='test control')

    revision = models.Revision.query.filter(
        models.Revision.resource_id == control.id,
        models.Revision.resource_type == control.type
    ).order_by(
        models.Revision.id.desc()
    ).first()

    snapshot = factories.SnapshotFactory(
        parent=audit,
        child_id=control.id,
        child_type=control.type,
        revision_id=revision.id
    )
    db.session.commit()

    # Act
    response, _ = self.objgen.generate_relationship(
        source=assessment,
        destination=snapshot,
        context=None,
    )
    assessment = self.refresh_object(assessment)
    # Assert
    self.assertStatus(response, 201)
    self.assertEqual(expected_status, assessment.status)

  @ddt.data(
      (models.Assessment.DONE_STATE, models.Assessment.PROGRESS_STATE),
      (models.Assessment.FINAL_STATE, models.Assessment.PROGRESS_STATE),
      (models.Assessment.START_STATE, models.Assessment.START_STATE),
      (models.Assessment.REWORK_NEEDED, models.Assessment.REWORK_NEEDED),
  )
  @ddt.unpack
  def test_unmapping_snapshot_status_check(self, from_status, expected_status):
    """When assessment in status '{0}' and
    un pamap Snapshot(type = assessment type)->
    status should be changed to '{1}'"""
    # Arrange
    with factories.single_commit():
      audit = factories.AuditFactory()
      assessment = factories.AssessmentFactory(audit=audit)
      factories.RelationshipFactory(source=audit, destination=assessment)
      control = factories.ControlFactory(title='test control')

    assessment_id = assessment.id

    revision = models.Revision.query.filter(
        models.Revision.resource_id == control.id,
        models.Revision.resource_type == control.type
    ).order_by(
        models.Revision.id.desc()
    ).first()

    snapshot = factories.SnapshotFactory(
        parent=audit,
        child_id=control.id,
        child_type=control.type,
        revision_id=revision.id
    )
    db.session.commit()

    response, relationship = self.objgen.generate_relationship(
        source=assessment,
        destination=snapshot,
        context=None,
    )
    assessment = self.refresh_object(assessment, assessment_id)

    assessment = self.change_status(assessment, from_status)
    assessment = self.refresh_object(assessment, assessment_id)
    self.assertEqual(from_status, assessment.status)

    # Act
    response = self.api.delete(relationship)
    assessment = self.refresh_object(assessment, assessment_id)

    # Assert
    self.assertStatus(response, 200)
    self.assertEqual(expected_status, assessment.status)

  @ddt.data(
      (models.Assessment.DONE_STATE, models.Assessment.PROGRESS_STATE),
      (models.Assessment.FINAL_STATE, models.Assessment.PROGRESS_STATE),
      (models.Assessment.START_STATE, models.Assessment.START_STATE),
      (models.Assessment.REWORK_NEEDED, models.Assessment.REWORK_NEEDED),
  )
  @ddt.unpack
  def test_mapping_snapshot_not_assessment_type(self, from_status,
                                                expected_status):
    """When assessment in status '{0}' and
     Map Snapshot(type = NOT assessment type)->
     status should be changed to '{1}'"""
    # Arrange
    with factories.single_commit():
      audit = factories.AuditFactory()
      assessment = factories.AssessmentFactory(audit=audit,
                                               status=from_status,
                                               assessment_type='Contract')
      factories.RelationshipFactory(source=audit, destination=assessment)
      control = factories.ControlFactory(title='test control')

    revision = models.Revision.query.filter(
        models.Revision.resource_id == control.id,
        models.Revision.resource_type == control.type
    ).order_by(
        models.Revision.id.desc()
    ).first()
    snapshot = factories.SnapshotFactory(
        parent=audit,
        child_id=control.id,
        child_type=control.type,
        revision_id=revision.id
    )
    db.session.commit()

    # Act
    response, _ = self.objgen.generate_relationship(
        source=assessment,
        destination=snapshot,
        context=None,
    )
    assessment = self.refresh_object(assessment)
    # Assert
    self.assertStatus(response, 201)
    self.assertEqual(expected_status, assessment.status)

  @ddt.data(
      (models.Assessment.DONE_STATE, models.Assessment.PROGRESS_STATE),
      (models.Assessment.FINAL_STATE, models.Assessment.PROGRESS_STATE),
      (models.Assessment.START_STATE, models.Assessment.START_STATE),
      (models.Assessment.REWORK_NEEDED, models.Assessment.REWORK_NEEDED),
  )
  @ddt.unpack
  def test_unmapping_snapshot_not_assessment_type(self, from_status,
                                                  expected_status):
    """When assessment in status '{0}' and
     unmap Snapshot(type = NOT assessment type)->
     status should be changed to '{1}'"""
    # Arrange
    with factories.single_commit():
      audit = factories.AuditFactory()
      assessment = factories.AssessmentFactory(audit=audit,
                                               assessment_type='Contract')
      factories.RelationshipFactory(source=audit, destination=assessment)
      control = factories.ControlFactory(title='test control')

    assessment_id = assessment.id

    revision = models.Revision.query.filter(
        models.Revision.resource_id == control.id,
        models.Revision.resource_type == control.type
    ).order_by(
        models.Revision.id.desc()
    ).first()

    snapshot = factories.SnapshotFactory(
        parent=audit,
        child_id=control.id,
        child_type=control.type,
        revision_id=revision.id
    )
    db.session.commit()

    response, relationship = self.objgen.generate_relationship(
        source=assessment,
        destination=snapshot,
        context=None,
    )
    assessment = self.refresh_object(assessment)

    assessment = self.change_status(assessment, from_status)
    assessment = self.refresh_object(assessment, assessment_id)

    self.assertEqual(from_status, assessment.status)

    # Act
    response = self.api.delete(relationship)
    assessment = self.refresh_object(assessment, assessment_id)

    # Assert
    self.assertStatus(response, 200)
    self.assertEqual(expected_status, assessment.status)


@ddt.ddt
class TestDocuments(TestMixinAutoStatusChangeableBase):
  """Test case for AutoStatusChangeable documents handlers"""
  # pylint: disable=invalid-name

  @ddt.data(
      ('REFERENCE_URL', models.Assessment.DONE_STATE,
       models.Assessment.PROGRESS_STATE),
      ('REFERENCE_URL', models.Assessment.START_STATE,
       models.Assessment.START_STATE),
      ('EVIDENCE', models.Assessment.DONE_STATE,
       models.Assessment.PROGRESS_STATE),
      ('EVIDENCE', models.Assessment.START_STATE,
       models.Assessment.PROGRESS_STATE),
      ('URL', models.Assessment.DONE_STATE,
       models.Assessment.PROGRESS_STATE),
      ('URL', models.Assessment.START_STATE,
       models.Assessment.PROGRESS_STATE),
  )
  @ddt.unpack
  def test_document_added_status_check(self, document_type,
                                       from_status, expected_status):
    """When assessment in status '{1}' and document type '{0}' added ->
     status should be changed to '{2}'"""
    # Arrange
    with factories.single_commit():
      assessment = factories.AssessmentFactory(status=from_status)

    related_document = {
        'id': None,
        'type': 'Document',
        'document_type': document_type,
        'title': 'google.com',
        'link': 'google.com',
    }

    # Act
    response = self.api.put(assessment, {'actions': {
        'add_related': [related_document]}
    })
    assessment = self.refresh_object(assessment)

    # Assert
    self.assert200(response)
    self.assertEqual(expected_status, assessment.status)

  @ddt.data(
      ('REFERENCE_URL', models.Assessment.DONE_STATE,
       models.Assessment.PROGRESS_STATE),
      ('REFERENCE_URL', models.Assessment.START_STATE,
       models.Assessment.START_STATE),
      ('EVIDENCE', models.Assessment.DONE_STATE,
       models.Assessment.PROGRESS_STATE),
      ('EVIDENCE', models.Assessment.START_STATE,
       models.Assessment.PROGRESS_STATE),
      ('URL', models.Assessment.DONE_STATE,
       models.Assessment.PROGRESS_STATE),
      ('URL', models.Assessment.START_STATE,
       models.Assessment.PROGRESS_STATE),
  )
  @ddt.unpack
  def test_document_remove_related(self, document_type,
                                   from_status, expected_status):
    """When assessment in status '{1}' and document type '{0}' removed ->
     status should be changed to '{2}'"""
    # Arrange
    with factories.single_commit():
      assessment = factories.AssessmentFactory(status=from_status)
      document = factories.DocumentFactory(document_type=document_type,
                                           title='google.com',
                                           link='google.com')
      factories.RelationshipFactory(destination=assessment, source=document)

    # Act
    response = self.api.put(assessment, {'actions': {'remove_related': [
        {
            'id': document.id,
            'type': 'Document',
        }
    ]}})
    assessment = self.refresh_object(assessment)
    # Assert
    self.assert200(response)
    self.assertEqual(expected_status, assessment.status)

  @ddt.data(
      ('REFERENCE_URL', models.Assessment.DONE_STATE,
       models.Assessment.PROGRESS_STATE),
      ('REFERENCE_URL', models.Assessment.START_STATE,
       models.Assessment.START_STATE),
      ('EVIDENCE', models.Assessment.DONE_STATE,
       models.Assessment.PROGRESS_STATE),
      ('EVIDENCE', models.Assessment.START_STATE,
       models.Assessment.PROGRESS_STATE),
      ('URL', models.Assessment.DONE_STATE,
       models.Assessment.PROGRESS_STATE),
      ('URL', models.Assessment.START_STATE,
       models.Assessment.PROGRESS_STATE),
  )
  @ddt.unpack
  def test_document_delete(self, document_type, from_status,
                           expected_status):
    """When assessment in status '{1}' and document type '{0}' deleted ->
    status should be changed to '{2}'"""
    # Arrange
    with factories.single_commit():
      assessment = factories.AssessmentFactory(status=from_status)
      document = factories.DocumentFactory(document_type=document_type,
                                           title='google.com',
                                           link='google.com')
      factories.RelationshipFactory(destination=assessment, source=document)

    assessment_id = assessment.id

    # Act
    response = self.api.delete(document)
    assessment = self.refresh_object(assessment, assessment_id)
    # Assert
    self.assert200(response)
    self.assertEqual(expected_status, assessment.status)

  @ddt.data(
      ('REFERENCE_URL', models.Assessment.DONE_STATE,
       models.Assessment.PROGRESS_STATE),
      ('REFERENCE_URL', models.Assessment.START_STATE,
       models.Assessment.START_STATE),
      ('EVIDENCE', models.Assessment.DONE_STATE,
       models.Assessment.PROGRESS_STATE),
      ('EVIDENCE', models.Assessment.START_STATE,
       models.Assessment.PROGRESS_STATE),
      ('URL', models.Assessment.DONE_STATE,
       models.Assessment.PROGRESS_STATE),
      ('URL', models.Assessment.START_STATE,
       models.Assessment.PROGRESS_STATE),
  )
  @ddt.unpack
  def test_document_update_status_check(self, document_type, from_status,
                                        expected_status):
    """When assessment in status '{1}' and document type '{0}' updated ->
     status should be changed to '{2}'"""
    # Arrange
    with factories.single_commit():
      assessment = factories.AssessmentFactory(status=from_status)
      document = factories.DocumentFactory(document_type=document_type,
                                           title='google.com',
                                           link='google.com')
      factories.RelationshipFactory(destination=assessment, source=document)

    assessment_id = assessment.id

    # Act
    response = self.api_helper.modify_object(document, {
        'title': 'New document',
        'link': 'New document',
    })

    assessment = self.refresh_object(assessment, assessment_id)
    # # Assert
    self.assert200(response)
    self.assertEqual(expected_status, assessment.status)


@ddt.ddt
class TestOther(TestMixinAutoStatusChangeableBase):
  """Test case for AutoStatusChangeable. Comment, custom access role,
   map/unmap issue, assignees Handlers"""
  # pylint: disable=invalid-name

  @ddt.data(
    (models.Assessment.DONE_STATE, models.Assessment.DONE_STATE),
    (models.Assessment.FINAL_STATE, models.Assessment.FINAL_STATE),
    (models.Assessment.START_STATE, models.Assessment.PROGRESS_STATE),
    (models.Assessment.REWORK_NEEDED, models.Assessment.REWORK_NEEDED),
  )
  @ddt.unpack
  def test_add_comment_status_check(self, from_status, expected_status):
    """When assessment in status '{0}' and comment added ->
    status should be changed to '{1}'"""
    # Arrange
    with factories.single_commit():
      assessment = factories.AssessmentFactory(status=from_status)

    # Act
    response = self.api.put(assessment, {'actions': {'add_related': [
        {
            'id': None,
            'type': 'Comment',
            'description': 'comment',
            'custom_attribute_definition_id': None,
        }
    ]}})
    assessment = self.refresh_object(assessment)

    # Assert
    self.assert200(response)
    self.assertEqual(expected_status, assessment.status)

  @ddt.data(models.Assessment.DONE_STATE,
            models.Assessment.FINAL_STATE,
            models.Assessment.PROGRESS_STATE,
            models.Assessment.REWORK_NEEDED
            )
  def test_custom_access_role_add_not_change_status(self, from_status):
    """Adding of 'custom access role' should not change status"""
    # Arrange
    with factories.single_commit():
      assessment = factories.AssessmentFactory(status=from_status)

    # Act
    factories.AccessControlRoleFactory(
        name='Test assessment role',
        object_type='Assessment',
    )
    assessment = self.refresh_object(assessment)

    # Assert
    self.assertEqual(from_status, assessment.status)

  @ddt.data(models.Assessment.DONE_STATE,
            models.Assessment.FINAL_STATE,
            models.Assessment.PROGRESS_STATE,
            models.Assessment.REWORK_NEEDED
            )
  def test_mapping_issue_not_change_status(self, from_status):
    """When assessment in status '{0}' and Map Issue ->
    status should NOT be changed"""
    # Arrange
    with factories.single_commit():
      audit = factories.AuditFactory()
      assessment = factories.AssessmentFactory(audit=audit,
                                               status=from_status,
                                               assessment_type='Contract')
      factories.RelationshipFactory(source=audit, destination=assessment)
      issue = factories.IssueFactory(title='test Issue')

    # Act
    response, _ = self.objgen.generate_relationship(
        source=assessment,
        destination=issue,
        context=None,
    )
    assessment = self.refresh_object(assessment)
    # Assert
    self.assertStatus(response, 201)
    self.assertEqual(from_status, assessment.status)

  @ddt.data(models.Assessment.DONE_STATE,
            models.Assessment.FINAL_STATE,
            models.Assessment.PROGRESS_STATE,
            models.Assessment.REWORK_NEEDED
            )
  def test_unmapping_issue_not_change_status(self, from_status):
    """When assessment in status '{0}' and unmap Issue->
    status should NOT be changed"""
    # Arrange
    with factories.single_commit():
      audit = factories.AuditFactory()
      assessment = factories.AssessmentFactory(audit=audit)
      factories.RelationshipFactory(source=audit, destination=assessment)
      issue = factories.IssueFactory(title='test Issue')

    assessment_id = assessment.id

    response, relationship = self.objgen.generate_relationship(
        source=assessment,
        destination=issue,
        context=None,
    )
    assessment = self.refresh_object(assessment, assessment_id)
    assessment = self.change_status(assessment, from_status)
    assessment = self.refresh_object(assessment, assessment_id)

    self.assertEqual(from_status, assessment.status)

    # Act
    response = self.api.delete(relationship)
    assessment = self.refresh_object(assessment, assessment_id)

    # Assert
    self.assertStatus(response, 200)
    self.assertEqual(from_status, assessment.status)

  @ddt.data(models.Assessment.DONE_STATE,
            models.Assessment.FINAL_STATE,
            models.Assessment.PROGRESS_STATE,
            models.Assessment.REWORK_NEEDED
            )
  def test_delete_issue_not_change_status(self, from_status):
    """When assessment in status '{0}' and Map Issue->
    status should NOT be changed"""
    # Arrange
    with factories.single_commit():
      audit = factories.AuditFactory()
      assessment = factories.AssessmentFactory(audit=audit)
      factories.RelationshipFactory(source=audit, destination=assessment)
      issue = factories.IssueFactory(title='test Issue')

    assessment_id = assessment.id

    self.objgen.generate_relationship(
        source=assessment,
        destination=issue,
        context=None,
    )
    assessment = self.refresh_object(assessment, assessment_id)
    assessment = self.change_status(assessment, from_status)
    assessment = self.refresh_object(assessment, assessment_id)

    self.assertEqual(from_status, assessment.status)

    # Act

    response = self.api.delete(issue)
    assessment = self.refresh_object(assessment, assessment_id)

    # Assert
    self.assertStatus(response, 200)
    self.assertEqual(from_status, assessment.status)

  @ddt.data("DONE_STATE", "START_STATE")
  def test_changing_assignees_should_not_change_status(self, test_state):
    """Adding/changing/removing assignees shouldn't change status

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
    """Test models.Assessment with verifiers full flow

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
