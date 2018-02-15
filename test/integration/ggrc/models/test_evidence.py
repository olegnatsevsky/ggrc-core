# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Integration tests for Evidence"""
from json import dumps

import ddt
from mock import mock

from ggrc.models import all_models
from integration.ggrc import TestCase
from integration.ggrc.access_control import acl_helper
from integration.ggrc.api_helper import Api
from integration.ggrc import generator
from integration.ggrc.models import factories

COPIED_TITLE = 'test_name'
COPIED_LINK = 'http://mega.doc'


def dummy_gdrive_response(*args, **kwargs):  # noqa
  return {'webViewLink': COPIED_LINK,
          'name': COPIED_TITLE}


@ddt.ddt
class TestEvidence(TestCase):
  """Evidence test cases"""

  # pylint: disable=invalid-name

  def setUp(self):
    super(TestEvidence, self).setUp()
    self.api = Api()
    self.gen = generator.ObjectGenerator()

  def create_evidence_by_api(self, kind=all_models.Evidence.URL):
    evidence_data = dict(
      title='Simple title',
      kind=kind,
      link='some_url.com',
      description='mega description'
    )
    resp, evidence = self.gen.generate_object(
        all_models.Evidence,
        evidence_data
    )

    result = all_models.Evidence.query.filter(
      all_models.Evidence.id == evidence.id).one()

    self.assertEqual(result.title, 'Simple title')
    self.assertEqual(result.kind, kind)
    self.assertFalse(result.archived)
    self.assertEqual(result.link, 'some_url.com')
    self.assertEqual(result.description, 'mega description')
    self.assertEqual(result.status, 'Active')

  @mock.patch('ggrc.gdrive.file_actions.process_gdrive_file', dummy_gdrive_response)
  def create_evidence_gdrive_type(self):
    with factories.single_commit():
      audit = factories.AuditFactory()
      assessment = factories.AssessmentFactory(audit=audit)
      evidence = factories.EvidenceFactory(
          title='Simple title',
          kind=all_models.Evidence.FILE,
          description='mega description',
          source_gdrive_id='gdrive_file_id',
          parent_obj={
              'id': assessment.id,
              'type': 'Assessment'
          }
      )

    result = all_models.Evidence.query.filter(
      all_models.Evidence.id == evidence.id).one()

    self.assertEqual(result.title, COPIED_TITLE)
    self.assertEqual(result.kind, all_models.Evidence.FILE)
    self.assertFalse(result.archived)
    self.assertEqual(result.link, COPIED_LINK)
    self.assertEqual(result.description, 'mega description')
    self.assertEqual(result.source_gdrive_id, 'gdrive_file_id')

  def test_create_invalid_type(self):
    """Test validation evidence_type."""
    data = {
        'kind': 'Wrong type',
        'title': 'test_title',
        'link': 'test_attachment',
    }
    obj_name = all_models.Evidence._inflector.table_singular
    obj = all_models.Evidence()
    obj_dict = self.gen.obj_to_dict(obj, obj_name)
    obj_dict[obj_name].update(data)
    resp = self.api.post(all_models.Evidence, obj_dict)
    self.assert400(resp)
    self.assertEqual('"Invalid value for attribute kind. '
                     'Expected options are `URL`, `FILE`"',
                     resp.data)

  @mock.patch('ggrc.gdrive.file_actions.process_gdrive_file', dummy_gdrive_response)
  def test_get_parent_obj_audit_type(self):
    """Test parent object audit"""
    audit = factories.AuditFactory()
    evidence = factories.EvidenceFactory(
        title='Simple title',
        kind=all_models.Evidence.FILE,
        link='some_url.com',
        description='mega description',
        source_gdrive_id='qwerqwer',
        parent_obj={
            'id': audit.id,
            'type': 'Audit'
        }
    )
    rel_asses = evidence.related_objects(_types=[audit.type])
    self.assertEqual(audit, rel_asses.pop())

  @mock.patch('ggrc.models.evidence.Evidence.handle_before_flush',
              lambda x: '')
  def test_evidence_postfix_audit(self):
    """Test evidence file postfix for audit."""

    audit = factories.AuditFactory()
    evidence = factories.EvidenceFactory(
        title='Simple title',
        kind=all_models.Evidence.FILE,
        link='some link',
        parent_obj={
            'id': audit.id,
            'type': 'Audit'
        })

    expected = '_ggrc_{}'.format(audit.slug).lower()
    # pylint: disable=protected-access
    result = evidence._build_file_name_postfix(audit)
    self.assertEqual(expected, result)

  @mock.patch('ggrc.models.evidence.Evidence.handle_before_flush',
              lambda x: '')
  def test_evidence_postfix_one_control(self):
    """Test evidence postfix for assessment with one control."""

    with factories.single_commit():
      audit = factories.AuditFactory()
      control = factories.ControlFactory()
      snapshot = self._create_snapshots(audit, [control])[0]
      assessment = factories.AssessmentFactory(audit=audit)
      factories.RelationshipFactory(source=assessment, destination=snapshot)

    evidence = factories.EvidenceFactory(
        title='Simple title',
        kind=all_models.Evidence.FILE,
        link='some link',
        parent_obj={
            'id': assessment.id,
            'type': 'Assessment'
        })

    expected = '_ggrc_assessment-{}_control-{}'.format(assessment.id,
                                                       control.id)
    # pylint: disable=protected-access
    result = evidence._build_file_name_postfix(assessment)
    self.assertEqual(expected, result)

  @mock.patch('ggrc.models.evidence.Evidence.handle_before_flush',
              lambda x: '')
  def test_evidence_postfix_two_controls(self):
    """Test evidence postfix for assessment with two controls."""

    with factories.single_commit():
      audit = factories.AuditFactory()
      control1 = factories.ControlFactory()
      control2 = factories.ControlFactory()
      snapshots = self._create_snapshots(audit, [control1, control2])
      assessment = factories.AssessmentFactory(audit=audit)
      factories.RelationshipFactory(source=assessment,
                                    destination=snapshots[0])
      factories.RelationshipFactory(source=assessment,
                                    destination=snapshots[1])

    evidence = factories.EvidenceFactory(
        title='Simple title',
        kind=all_models.Evidence.FILE,
        link='some link',
        parent_obj={
            'id': assessment.id,
            'type': 'Assessment'
        })

    expec = '_ggrc_assessment-{}_control-{}_control-{}'.format(assessment.id,
                                                               control1.id,
                                                               control2.id)
    # pylint: disable=protected-access
    result = evidence._build_file_name_postfix(assessment)
    self.assertEqual(expec, result)

  def test_evidence_acl(self):
    """Test evidence with ACR creation"""
    person = factories.PersonFactory()
    acr_class = all_models.AccessControlRole
    acr = acr_class.query.filter(acr_class.name == 'Admin',
                                 acr_class.object_type == 'Evidence').one()

    evidence = factories.EvidenceFactory(
      title='Simple title',
      kind=all_models.Evidence.URL,
      link='simple_url.test',
      access_control_list=[
        acl_helper.get_acl_json(acr.id, person.id)
      ]
    )
    acl_class = all_models.AccessControlList
    acl = acl_class.query.filter(
      acl_class.object_id == evidence.id).one()
    self.assertTrue(acl)

  @ddt.data(True, False)
  def test_archived_audit(self, archived):
    audit = factories.AuditFactory(archived=archived)

    evidence = factories.EvidenceFactory(
      title='Simple title',
      kind=all_models.Evidence.URL,
      link='some_url.com',
      description='mega description',
      parent_obj={
        'id': audit.id,
        'type': 'Audit'
      }
    )
    self.assertEquals(archived, evidence.archived)

  @ddt.data(True, False)
  def test_archived_assessment(self, archived):
    with factories.single_commit():
      audit = factories.AuditFactory(archived=archived)
      control = factories.ControlFactory()
      snapshot = self._create_snapshots(audit, [control])[0]
      assessment = factories.AssessmentFactory(audit=audit)
      factories.RelationshipFactory(source=assessment, destination=snapshot)

    evidence = factories.EvidenceFactory(
      title='Simple title',
      kind=all_models.Evidence.URL,
      link='some link',
      parent_obj={
        'id': assessment.id,
        'type': 'Assessment'
      })
    self.assertEquals(archived, evidence.archived)

  def test_evidence_url_type_with_parent(self):
    """Evidence of URL type should mapped to parent if parent specified"""
    audit = factories.AuditFactory()
    evidence = factories.EvidenceFactory(
      title='Simple title',
      kind=all_models.Evidence.URL,
      link='some_url.com',
      description='mega description',
      parent_obj={
        'id': audit.id,
        'type': 'Audit'
      }
    )
    rel_evidences = audit.related_objects(_types=[evidence.type])
    self.assertEqual(evidence, rel_evidences.pop())

