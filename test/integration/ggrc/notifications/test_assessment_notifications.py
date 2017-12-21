# Copyright (C) 2017 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Tests of assessment notifications."""
from ggrc import db
from ggrc.notifications import common
from ggrc.models import Person, Assessment, AccessControlRole
from ggrc.models import all_models
from integration.ggrc import api_helper
from integration.ggrc import TestCase
from integration.ggrc.models import factories


class TestAssessmentNotification(TestCase):
  """Tests of assessment notifications"""

  @classmethod
  def setUpClass(cls):
    """Set up test cases for all tests."""
    cls.primary_role_id = AccessControlRole.query.filter_by(
        object_type="Assessment",
        name="Primary Contacts"
    ).first().id

    cls.secondary_role_id = AccessControlRole.query.filter_by(
        object_type="Assessment",
        name="Secondary Contacts"
    ).first().id

  def setUp(self):
    super(TestAssessmentNotification, self).setUp()
    self.client.get("/login")
    self.api = api_helper.Api()
    self.auditor = Person.query.filter_by(email="user@example.com").one()
    self.api.set_user(self.auditor)
    audit = factories.AuditFactory()
    assignee_acr = all_models.AccessControlRole.query.filter_by(
        object_type="Assessment",
        name="Assignees",
    ).first()

    self.api.post(Assessment, {
        "assessment": {
            "title": "Assessment1",
            "context": None,
            "audit": {
                "id": audit.id,
                "type": "Audit",
            },
            "access_control_list": [
                {
                    "person": {
                        "id": self.auditor.id,
                        "type": "Person",
                    },
                    "ac_role_id": self.primary_role_id,
                    "context": None
                },
                {
                    "person": {
                        "id": self.auditor.id,
                        "type": "Person",
                    },
                    "ac_role_id": assignee_acr.id,
                    "context": None
                }
            ],
            "status": "In Progress",
        }
    })

    self.assessment = Assessment.query.filter_by(title="Assessment1").one()

    self.cad1 = factories.CustomAttributeDefinitionFactory(
        definition_type="assessment",
        title="ca1",
    )
    factories.CustomAttributeValueFactory(
        custom_attribute=self.cad1,
        attributable=self.assessment
    )
    self.cad3 = factories.CustomAttributeDefinitionFactory(
        definition_type="assessment",
        attribute_type="Checkbox",
        title="ca3",
    )
    factories.CustomAttributeValueFactory(
        custom_attribute=self.cad3,
        attributable=self.assessment
    )

    db.engine.execute(
        """
            UPDATE notifications
               SET sent_at = NOW()
        """
    )

  def test_common_attr_change(self):
    """Test notification when common attribute value is changed"""
    response = self.api.put(self.assessment, {"test_plan": "steps"})
    self.assert200(response)

    notifs, notif_data = common.get_daily_notifications()
    updated = notif_data["user@example.com"]["assessment_updated"]
    self.assertEqual(len(notifs), 1)
    self.assertEqual(updated[self.assessment.id]["updated_fields"],
                     ["ASSESSMENT PROCEDURE"])

  def test_custom_attr_change(self):
    """Test notification when custom attribute value is changed"""
    custom_attribute_values = [{
        "custom_attribute_id": self.cad1.id,
        "attribute_value": "test value",
    }]
    response = self.api.put(self.assessment, {
        "custom_attribute_values": custom_attribute_values
    })
    self.assert200(response)

    notifs, notif_data = common.get_daily_notifications()
    updated = notif_data["user@example.com"]["assessment_updated"]
    self.assertEqual(len(notifs), 1)
    self.assertEqual(updated[self.assessment.id]["updated_fields"], ["CA1"])

  def test_checkbox_attr_change(self):
    """Test notification when person attribute value is changed"""
    custom_attribute_values = [{
        "custom_attribute_id": self.cad3.id,
        "attribute_value": "1",
    }]
    response = self.api.put(self.assessment, {
        "custom_attribute_values": custom_attribute_values
    })
    self.assert200(response)

    notifs, notif_data = common.get_daily_notifications()
    updated = notif_data["user@example.com"]["assessment_updated"]
    self.assertEqual(len(notifs), 1)
    self.assertEqual(
        updated[self.assessment.id]["updated_fields"], ["CA3"])

  def test_access_conrol_list(self):
    """Test notification when access conrol list is changed"""
    assignee_acr = all_models.AccessControlRole.query.filter_by(
        object_type="Assessment",
        name="Assignees",
    ).first()
    response = self.api.put(self.assessment, {
        "access_control_list": [
            {
                "person": {
                    "id": self.auditor.id,
                    "type": "Person",
                },
                "ac_role_id": self.secondary_role_id,
                "context": None
            },
            {
                "person": {
                    "id": self.auditor.id,
                    "type": "Person",
                },
                "ac_role_id": assignee_acr.id,
                "context": None
            }
        ],
    })
    self.assert200(response)

    notifs, notif_data = common.get_daily_notifications()
    updated = notif_data["user@example.com"]["assessment_updated"]
    self.assertEqual(len(notifs), 1)
    self.assertEqual(updated[self.assessment.id]["updated_fields"],
                     ["PRIMARY CONTACTS", "SECONDARY CONTACTS"])

  def test_multiply_updates(self):
    """Test notification for multiply updates"""
    response = self.api.put(self.assessment, {"test_plan": "steps"})
    self.assert200(response)

    response = self.api.put(self.assessment, {"title": "new title"})
    self.assert200(response)

    notifs, notif_data = common.get_daily_notifications()
    updated = notif_data["user@example.com"]["assessment_updated"]
    self.assertEqual(len(notifs), 1)
    self.assertEqual(sorted(updated[self.assessment.id]["updated_fields"]),
                     ["ASSESSMENT PROCEDURE", "TITLE"])

  def test_multiply_mapping(self):
    """Test notification for multiply mapping"""
    controls = [factories.ControlFactory() for _ in xrange(5)]
    snapshots = self._create_snapshots(self.assessment.audit, controls)

    def get_relation_dict(destination_obj):
      return {
          "relationship": {
              "context": {"id": self.assessment.audit.context.id,
                          "type": self.assessment.audit.context.type},
              "source": {"id": self.assessment.id,
                         "type": self.assessment.type},
              "destination": {"id": destination_obj.id,
                              "type": destination_obj.type}
          }
      }
    notifs, _ = common.get_daily_notifications()
    self.assertFalse(len(notifs))
    self.assessment.status = "In Progress"
    post_data = [get_relation_dict(s) for s in snapshots]
    db.session.add(self.assessment)
    resp = self.api.send_request(
        self.api.client.post, obj=all_models.Relationship, data=post_data)
    self.assert200(resp)
    notifs, _ = common.get_daily_notifications()
    self.assertEqual(len(notifs), 1)
