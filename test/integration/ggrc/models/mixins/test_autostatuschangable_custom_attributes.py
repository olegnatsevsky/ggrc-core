# Copyright (C) 2017 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Integration test for AutoStatusChangeable mixin custom attributes"""

import ddt

from ggrc import models
from integration.ggrc.models import factories
from integration.ggrc.models.mixins.test_autostatuschangable import \
  TestMixinAutoStatusChangeableBase


@ddt.ddt
class TestCustomAttributes(TestMixinAutoStatusChangeableBase):
  """Test case for AutoStatusChangeable custom attributes handlers"""
  # pylint: disable=invalid-name

  @ddt.data(models.Assessment.DONE_STATE,
            models.Assessment.FINAL_STATE,
            models.Assessment.PROGRESS_STATE,
            models.Assessment.REWORK_NEEDED
            )
  def test_global_ca_admin_add_not_change_status(self, from_status):
    """Adding of 'global custom attribute' should not change status"""
    # Arrange
    with factories.single_commit():
      assessment = factories.AssessmentFactory(status=from_status)

    # Act
    with factories.single_commit():
      factories.CustomAttributeDefinitionFactory(definition_type='assessment',
                                                 attribute_type='Rich Text',
                                                 title='rich_test_gca',
                                                 multi_choice_options=''
                                                 )
    assessment = self.refresh_object(assessment)
    # Assert
    self.assertEqual(from_status, assessment.status)

  @ddt.data(
      (models.Assessment.DONE_STATE, models.Assessment.PROGRESS_STATE),
      (models.Assessment.FINAL_STATE, models.Assessment.PROGRESS_STATE),
      (models.Assessment.START_STATE, models.Assessment.START_STATE),
      (models.Assessment.REWORK_NEEDED, models.Assessment.REWORK_NEEDED),
  )
  @ddt.unpack
  def test_global_ca_update_change_status(self, from_status, expected_status):
    """When assessment in status '{0}' and 'global custom attribute' updated ->
     status should be changed to '{1}'"""

    # Arrange
    with factories.single_commit():
      ca_factory = factories.CustomAttributeDefinitionFactory
      gca = ca_factory(definition_type='assessment',
                       title='rich_test_gca',
                       attribute_type='Rich Text',
                       multi_choice_options=''
                       )
      assessment = factories.AssessmentFactory(status=from_status)

    # Act
    self.api_helper.modify_object(assessment, {
        'custom_attribute_values': [{
            'custom_attribute_id': gca.id,
            'attribute_value': 'new value',
        }]
    })
    assessment = self.refresh_object(assessment)

    # Assert
    self.assertEqual(expected_status, assessment.status)

  @ddt.data(
      (models.Assessment.DONE_STATE, models.Assessment.PROGRESS_STATE),
      (models.Assessment.FINAL_STATE, models.Assessment.PROGRESS_STATE),
      (models.Assessment.START_STATE, models.Assessment.PROGRESS_STATE),
      (models.Assessment.REWORK_NEEDED, models.Assessment.REWORK_NEEDED),
  )
  @ddt.unpack
  def test_local_ca_update_change_status(self, from_status, expected_status):
    """When assessment in status '{0}' and 'local custom attribute' updated ->
    status should be changed to '{1}'"""
    # Arrange
    with factories.single_commit():
      audit = factories.AuditFactory()
      assessment = factories.AssessmentFactory(audit=audit, status=from_status)
      factories.RelationshipFactory(source=audit, destination=assessment)

      cad = factories.CustomAttributeDefinitionFactory(
          definition_id=assessment.id,
          definition_type='assessment',
          attribute_type='Rich Text',
          title='rich_test_gca',
          multi_choice_options='',
      )

    # Act
    self.api_helper.modify_object(assessment, {
        'custom_attribute_values': [{
            'custom_attribute_id': cad.id,
            'attribute_value': 'new value',
        }]
    })
    assessment = self.refresh_object(assessment)

    # Assert
    self.assertEqual(expected_status, assessment.status)
