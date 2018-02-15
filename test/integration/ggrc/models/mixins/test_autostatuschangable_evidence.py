# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Integration test for AutoStatusChangeable mixin related evidence"""

import ddt

from ggrc import models
from integration.ggrc.models import factories
from integration.ggrc.models.mixins.test_autostatuschangable import TestMixinAutoStatusChangeableBase


@ddt.ddt
class TestEvidences(TestMixinAutoStatusChangeableBase):
  """Test case for AutoStatusChangeable evidences handlers"""
  # pylint: disable=invalid-name

  @ddt.data(
    ('URL', models.Assessment.DONE_STATE,
     models.Assessment.PROGRESS_STATE),
    ('URL', models.Assessment.START_STATE,
     models.Assessment.PROGRESS_STATE),
    ('FILE', models.Assessment.DONE_STATE,
     models.Assessment.PROGRESS_STATE),
    ('FILE', models.Assessment.START_STATE,
     models.Assessment.PROGRESS_STATE)
  )
  @ddt.unpack
  def test_evidence_added_status_check(self, kind,
                                       from_status, expected_status):
    """Move Assessment from '{1}' to '{2}' adding evidence of type {0}"""
    assessment = factories.AssessmentFactory(status=from_status)
    related_evidence = {
      'id': None,
      'type': 'Evidence',
      'kind': kind,
      'title': 'google.com',
      'link': 'google.com',
      'source_gdrive_id': 'some_id'
    }
    response = self.api.put(assessment, {
      'actions': {
        'add_related': [related_evidence]
      }
    })
    assessment = self.refresh_object(assessment)
    self.assert200(response, response.json)
    self.assertEqual(expected_status, assessment.status)

  @ddt.data(
    ('FILE', models.Assessment.DONE_STATE,
     models.Assessment.PROGRESS_STATE),
    ('FILE', models.Assessment.START_STATE,
     models.Assessment.PROGRESS_STATE),
    ('URL', models.Assessment.DONE_STATE,
     models.Assessment.PROGRESS_STATE),
    ('URL', models.Assessment.START_STATE,
     models.Assessment.PROGRESS_STATE),
  )
  @ddt.unpack
  def test_evidence_remove_related(self, kind,
                                   from_status, expected_status):
    """Move Assessment from '{1}' to '{2}' remove evidence of type {0}"""
    with factories.single_commit():
      assessment = factories.AssessmentFactory(status=from_status)
      evidence = factories.EvidenceFactory(kind=kind,
                                           title='google.com',
                                           link='google.com',
                                           source_gdrive_id='some_id')
      factories.RelationshipFactory(destination=assessment, source=evidence)

    response = self.api.put(assessment, {
      'actions': {
        'remove_related': [{
          'id': evidence.id,
          'type': 'Evidence',
        }]
      }
    })
    assessment = self.refresh_object(assessment)
    self.assert200(response)
    self.assertEqual(expected_status, assessment.status)

  @ddt.data(
    ('FILE', models.Assessment.DONE_STATE,
     models.Assessment.PROGRESS_STATE),
    ('FILE', models.Assessment.START_STATE,
     models.Assessment.PROGRESS_STATE),
    ('URL', models.Assessment.DONE_STATE,
     models.Assessment.PROGRESS_STATE),
    ('URL', models.Assessment.START_STATE,
     models.Assessment.PROGRESS_STATE),
  )
  @ddt.unpack
  def test_evidence_delete(self, kind, from_status,
                           expected_status):
    """Move Assessment from '{1}' to '{2}' delete evidence of type {0}"""
    with factories.single_commit():
      assessment = factories.AssessmentFactory(status=from_status)
      evidence = factories.EvidenceFactory(kind=kind,
                                           title='google.com',
                                           link='google.com',
                                           source_gdrive_id='some_id')
      factories.RelationshipFactory(destination=assessment, source=evidence)
    assessment_id = assessment.id
    response = self.api.delete(evidence)
    assessment = self.refresh_object(assessment, assessment_id)
    self.assert200(response)
    self.assertEqual(expected_status, assessment.status)

  @ddt.data(
    ('FILE', models.Assessment.DONE_STATE,
     models.Assessment.PROGRESS_STATE),
    ('FILE', models.Assessment.START_STATE,
     models.Assessment.PROGRESS_STATE),
    ('URL', models.Assessment.DONE_STATE,
     models.Assessment.PROGRESS_STATE),
    ('URL', models.Assessment.START_STATE,
     models.Assessment.PROGRESS_STATE),
  )
  @ddt.unpack
  def test_evidence_update_status_check(self, kind, from_status,
                                        expected_status):
    """Move Assessment from '{1}' to '{2}' update evidence of type {0}"""
    with factories.single_commit():
      assessment = factories.AssessmentFactory(status=from_status)
      evidence = factories.EvidenceFactory(kind=kind,
                                           title='google.com',
                                           link='google.com',
                                           source_gdrive_id='some_id')
      factories.RelationshipFactory(destination=assessment, source=evidence)
    assessment_id = assessment.id
    response = self.api.modify_object(evidence, {
      'title': 'New evidence',
      'link': 'New evidence',
    })
    assessment = self.refresh_object(assessment, assessment_id)
    self.assert200(response)
    self.assertEqual(expected_status, assessment.status)
