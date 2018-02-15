# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Test Access Control Propagation for Evidence Roles"""
import ddt


from ggrc.models import all_models
from integration.ggrc import TestCase, Api
from integration.ggrc.generator import ObjectGenerator
from integration.ggrc.models import factories


@ddt.ddt
class TestEvidenceRolePropagation(TestCase):
  def setUp(self):
    super(TestEvidenceRolePropagation, self).setUp()
    self.api = Api()
    self.generator = ObjectGenerator()

  # Propagation isn't work for 'Primary Contacts', 'Secondary Contacts'
  # just add them to data list to check if fix works.

  @ddt.data("Assignees", "Creators", "Verifiers")
  def test_assessment_role_propagation_edit(self, role):
    """Asses user with role '{0}' should be able to edit related evidence"""

    _, reader = self.generator.generate_person(user_role="Creator")
    assignees_role = all_models.AccessControlRole.query.filter_by(
      object_type=all_models.Assessment.__name__, name=role
    ).first()

    with factories.single_commit():
      assessment = factories.AssessmentFactory()
      factories.AccessControlListFactory(
        ac_role=assignees_role,
        object=assessment,
        person=reader
      )
      evidence = factories.EvidenceFactory()
      evidence_id = evidence.id
      factories.RelationshipFactory(source=assessment, destination=evidence)

    self.api.set_user(reader)

    evidence = all_models.Evidence.query.get(evidence_id)
    new_description = 'new description'
    resp = self.api.modify_object(evidence, {'description': new_description})
    evidence = self.refresh_object(evidence)
    self.assert200(resp)
    self.assertEquals(new_description, evidence.description)
    self.assertEquals(reader.id, evidence.modified_by_id)

  # Propagation isn't work for 'Primary Contacts', 'Secondary Contacts'
  # just add them to data list to check if fix works.
  @ddt.data("Assignees", "Creators", "Verifiers")
  def test_assessment_role_propagation_delete(self, role):
    """Asses user with role '{0}' should be able to delete related evidence"""
    _, reader = self.generator.generate_person(user_role="Creator")
    assignees_role = all_models.AccessControlRole.query.filter_by(
      object_type=all_models.Assessment.__name__, name=role
    ).first()

    with factories.single_commit():
      assessment = factories.AssessmentFactory()
      factories.AccessControlListFactory(
        ac_role=assignees_role,
        object=assessment,
        person=reader
      )
      evidence = factories.EvidenceFactory()
      evidence_id = evidence.id
      factories.RelationshipFactory(source=assessment, destination=evidence)

    self.api.set_user(reader)

    evidence = all_models.Evidence.query.get(evidence_id)
    resp = self.api.delete(evidence)
    self.assert200(resp)
    evidence = all_models.Evidence.query.get(evidence_id)
    self.assertFalse(evidence)

  @ddt.data("Audit Captains", "Auditors")
  def test_audit_role_propagation_edit(self, role):
    """Audit user with role '{0}' should be able to edit related evidence"""
    _, reader = self.generator.generate_person(user_role="Reader")
    assignees_role = all_models.AccessControlRole.query.filter_by(
      object_type=all_models.Audit.__name__, name=role
    ).first()
    with factories.single_commit():
      audit = factories.AuditFactory()
      factories.AccessControlListFactory(
        ac_role=assignees_role,
        object=audit,
        person=reader
      )
      evidence = factories.EvidenceFactory()
      evidence_id = evidence.id

    factories.RelationshipFactory(source=audit, destination=evidence)

    self.api.set_user(reader)

    evidence = all_models.Evidence.query.get(evidence_id)
    new_description = 'new description'
    resp = self.api.modify_object(evidence, {'description': new_description})
    evidence = self.refresh_object(evidence)
    self.assert200(resp)
    self.assertEquals(new_description, evidence.description)
    self.assertEquals(reader.id, evidence.modified_by_id)

  def test_audit_role_propagation_delete(self, role="Audit Captains"):
    """Audit user with role 'Audit Captains' can delete mapped evidence"""

    _, reader = self.generator.generate_person(user_role="Reader")
    assignees_role = all_models.AccessControlRole.query.filter_by(
      object_type=all_models.Audit.__name__, name=role
    ).first()
    with factories.single_commit():
      audit = factories.AuditFactory()
      factories.AccessControlListFactory(
        ac_role=assignees_role,
        object=audit,
        person=reader
      )
      evidence = factories.EvidenceFactory()
      evidence_id = evidence.id

    factories.RelationshipFactory(source=audit, destination=evidence)
    # Weird that Evidence get 'Audit Captains Mapped' role for Audit object
    # proper way is to create 'Audit Captains Evidence Mapped' for Evidence object

    self.api.set_user(reader)
    evidence = all_models.Evidence.query.get(evidence_id)

    resp = self.api.delete(evidence)
    self.assert200(resp)
    evidence = all_models.Evidence.query.get(evidence_id)
    self.assertFalse(evidence)

  def test_audit_role_propagation_not_delete(self, role="Auditors"):
    """Audit user with role Auditors can NOT delete related evidence"""

    _, reader = self.generator.generate_person(user_role="Reader")
    assignees_role = all_models.AccessControlRole.query.filter_by(
      object_type=all_models.Audit.__name__, name=role
    ).first()
    with factories.single_commit():
      audit = factories.AuditFactory()
      factories.AccessControlListFactory(
        ac_role=assignees_role,
        object=audit,
        person=reader
      )
      evidence = factories.EvidenceFactory()
      evidence_id = evidence.id

    factories.RelationshipFactory(source=audit, destination=evidence)

    self.api.set_user(reader)
    evidence = all_models.Evidence.query.get(evidence_id)

    resp = self.api.delete(evidence)
    self.assertStatus(resp, 403)
    evidence = all_models.Evidence.query.get(evidence_id)
    self.assertTrue(evidence)

  def test_audit_assessment_role_propagation_delete(self, role="Audit Captains"):
    """Audit user with role Audit Captains can delete assess mapped evid"""

    _, reader = self.generator.generate_person(user_role="Reader")
    audit = factories.AuditFactory()
    with factories.single_commit():
      assessment = factories.AssessmentFactory(audit=audit)
      ac_role = all_models.AccessControlRole.query.filter_by(
        object_type=audit.type, name=role
      ).first()
      factories.AccessControlListFactory(
        ac_role=ac_role,
        object=audit,
        person=reader
      )
      factories.RelationshipFactory(source=audit, destination=assessment)
      evidence = factories.EvidenceFactory()
      evidence_id = evidence.id
      factories.RelationshipFactory(source=assessment, destination=evidence)

    self.api.set_user(reader)
    evidence = all_models.Evidence.query.get(evidence_id)

    resp = self.api.delete(evidence)
    self.assert200(resp)
    self.assertFalse(all_models.Evidence.query.filter(
      all_models.Evidence.id == evidence.id).all())
