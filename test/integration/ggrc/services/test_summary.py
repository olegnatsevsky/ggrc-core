# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
Test /summary endpoint
"""
import ddt

from ggrc.models import all_models
from integration.ggrc import TestCase
from integration.ggrc.api_helper import Api
from integration.ggrc.models import factories


@ddt.ddt
class TestAuditSummary(TestCase):
  """Test /summary for Audit"""

  def setUp(self):
    """Set up for test methods."""
    super(TestAuditSummary, self).setUp()
    self.api = Api()

  def test_evidence_filter(self):
    """Only evidence kind URL and FILE should be shown in summary"""
    with factories.single_commit():
      audit = factories.AuditFactory()
      assessment = factories.AssessmentFactory(audit=audit)

      evidence_url = factories.EvidenceFactory(kind=all_models.Evidence.URL)
      factories.RelationshipFactory(source=evidence_url, destination=assessment)

      evidence_reference_url = factories.EvidenceFactory(kind=all_models.Evidence.REFERENCE_URL)
      factories.RelationshipFactory(source=assessment, destination=evidence_reference_url)

      evidence_file = factories.EvidenceFactory(kind=all_models.Evidence.FILE,
                                                source_gdrive_id='12345')
      factories.RelationshipFactory(source=assessment, destination=evidence_file)

    summary_link = "/api/{}/{}/summary".format(
      audit._inflector.table_plural, audit.id
    )
    response = self.api.client.get(summary_link)
    self.assert200(response)
    self.assertEqual(response.json['total']['evidences'], 2)

  def test_assessment_no_evidence_filter(self):
    """Summary should show proper number of assessments.

    When no evidences attached.
    """
    with factories.single_commit():
      audit = factories.AuditFactory()
      factories.AssessmentFactory(audit=audit)
      factories.AssessmentFactory(audit=audit)

    summary_link = "/api/{}/{}/summary".format(
      audit._inflector.table_plural, audit.id
    )
    response = self.api.client.get(summary_link)
    self.assert200(response)
    self.assertEqual(response.json["total"]["assessments"], 2)

  @ddt.data(1, 2)
  def test_audit_summary(self, assessment_count):
    """Test Audit summary when each type of Asmnt linked to each Evid type"""
    with factories.single_commit():
      audit = factories.AuditFactory()
      for status in all_models.Assessment.VALID_STATES:
        for _ in range(assessment_count):
          assessment = factories.AssessmentFactory(audit=audit, status=status)
          evidence_url = factories.EvidenceFactory(kind=all_models.Evidence.URL)
          factories.RelationshipFactory(source=assessment, destination=evidence_url)

          evidence_reference_url = factories.EvidenceFactory(kind=all_models.Evidence.REFERENCE_URL)
          factories.RelationshipFactory(source=assessment, destination=evidence_reference_url)

          evidence_file = factories.EvidenceFactory(kind=all_models.Evidence.FILE,
                                                    source_gdrive_id='12345')
          factories.RelationshipFactory(source=assessment, destination=evidence_file)

    summary_link = "/api/{}/{}/summary".format(
        audit._inflector.table_plural, audit.id
    )
    response = self.api.client.get(summary_link)
    self.assert200(response)

    evid_count = len(all_models.Evidence.VALID_EVIDENCE_KINDS) - 1 # -1 for REFERENCE_URL
    expected_data = {
        "statuses": [
            {
                "name": "Completed",
                "assessments": assessment_count,
                "evidences": evid_count * assessment_count,
                "verified": 0
            },
            {
                "name": "Completed",
                "assessments": assessment_count,
                "evidences": evid_count * assessment_count,
                "verified": 1
            },
            {
                "name": "Deprecated",
                "assessments": assessment_count,
                "evidences": evid_count * assessment_count,
                "verified": 0
            },
            {
                "name": "In Progress",
                "assessments": assessment_count,
                "evidences": evid_count * assessment_count,
                "verified": 0
            },
            {
                "name": "In Review",
                "assessments": assessment_count,
                "evidences": evid_count * assessment_count,
                "verified": 0
            },
            {
                "name": "Not Started",
                "assessments": assessment_count,
                "evidences": evid_count * assessment_count,
                "verified": 0
            },
            {
                "name": "Rework Needed",
                "assessments": assessment_count,
                "evidences": evid_count * assessment_count,
                "verified": 0
            }
        ],
        "total": {
            "assessments": 7 * assessment_count,
            "evidences": 7 * evid_count * assessment_count
        }
    }
    self.assertEqual(response.json, expected_data)

  def test_asmnt_map_same_docs(self):
    """Test Audit summary when all Assessments mapped to same Evidences"""
    with factories.single_commit():
      audit = factories.AuditFactory()
      asmnt_statuses = all_models.Assessment.VALID_STATES
      evidences = [
        factories.EvidenceFactory(kind=all_models.Evidence.URL),
        factories.EvidenceFactory(kind=all_models.Evidence.REFERENCE_URL),
        factories.EvidenceFactory(kind=all_models.Evidence.FILE,
                                  source_gdrive_id='12345')
      ]
      for status in asmnt_statuses:
        asmnt = factories.AssessmentFactory(audit=audit, status=status)
        for evidence in evidences:
          factories.RelationshipFactory(source=asmnt, destination=evidence)

    summary_link = "/api/{}/{}/summary".format(
        audit._inflector.table_plural, audit.id
    )
    response = self.api.client.get(summary_link)
    self.assert200(response)

    evid_count = len(all_models.Evidence.VALID_EVIDENCE_KINDS) - 1 # -1 for REFERENCE_URL
    expected_data = {
        "statuses": [
            {
                "name": "Completed",
                "assessments": 1,
                "evidences": evid_count,
                "verified": 0
            },
            {
                "name": "Completed",
                "assessments": 1,
                "evidences": evid_count,
                "verified": 1
            },
            {
                "name": "Deprecated",
                "assessments": 1,
                "evidences": evid_count,
                "verified": 0
            },
            {
                "name": "In Progress",
                "assessments": 1,
                "evidences": evid_count,
                "verified": 0
            },
            {
                "name": "In Review",
                "assessments": 1,
                "evidences": evid_count,
                "verified": 0
            },
            {
                "name": "Not Started",
                "assessments": 1,
                "evidences": evid_count,
                "verified": 0
            },
            {
                "name": "Rework Needed",
                "assessments": 1,
                "evidences": evid_count,
                "verified": 0
            }
        ],
        "total": {
            "assessments": 7,
            "evidences": evid_count
        }
    }
    self.assertEqual(response.json, expected_data)

  def test_part_asmnt_exist(self):
    """Test Audit summary when not all kinds of Asmnt created"""
    with factories.single_commit():
      audit = factories.AuditFactory()
      for status in ["Completed", "Verified"]:
        assessment = factories.AssessmentFactory(audit=audit, status=status)
        evidence_url = factories.EvidenceFactory(kind=all_models.Evidence.URL)
        factories.RelationshipFactory(source=assessment, destination=evidence_url)

        evidence_reference_url = factories.EvidenceFactory(kind=all_models.Evidence.REFERENCE_URL)
        factories.RelationshipFactory(source=assessment, destination=evidence_reference_url)

        evidence_file = factories.EvidenceFactory(kind=all_models.Evidence.FILE,
                                                  source_gdrive_id='12345')
        factories.RelationshipFactory(source=assessment, destination=evidence_file)

    summary_link = "/api/{}/{}/summary".format(
        audit._inflector.table_plural, audit.id
    )
    response = self.api.client.get(summary_link)
    self.assert200(response)

    evid_count = len(all_models.Evidence.VALID_EVIDENCE_KINDS) - 1 # -1 for REFERENCE_URL
    expected_data = {
        "statuses": [
            {
                "name": "Completed",
                "assessments": 1,
                "evidences": evid_count,
                "verified": 0
            },
            {
                "name": "Completed",
                "assessments": 1,
                "evidences": evid_count,
                "verified": 1
            },
        ],
        "total": {
            "assessments": 2,
            "evidences": 2 * evid_count
        }
    }
    self.assertEqual(response.json, expected_data)

  def test_empty_audit_summary(self):
    """Test Audit summary if there are no assessments"""
    audit = factories.AuditFactory()

    summary_link = "/api/{}/{}/summary".format(
        audit._inflector.table_plural, audit.id
    )
    response = self.api.client.get(summary_link)
    expected_data = {
        "statuses": [],
        "total": {
            "assessments": 0,
            "evidences": 0,
        }
    }
    self.assertEqual(response.json, expected_data)
