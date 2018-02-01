# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Integration tests for Assessment Template"""
from ggrc.models import all_models
from ggrc.models import AssessmentTemplate
from integration.ggrc.models import factories
from integration.ggrc.models.test_assessment_base import TestAssessmentBase


class TestAssessmentTemplate(TestAssessmentBase):
  """Test assessment template"""

  def test_template_lca_person_type(self):
    """Test creation of assessment template with LCA in one POST"""
    with factories.single_commit():
      audit = factories.AuditFactory()
      context = factories.ContextFactory()

    template_title = 'template_title'
    lca_title = 'lca_title'

    request_data = {
        'assessment_template': {
            'template_object_type': 'Control',
            'default_people': {
                'assignees': 'Principal Assignees',
                'verifiers': 'Auditors'
            },

            'custom_attributes': {},
            'custom_attribute_definitions': [{
                'title': lca_title,
                'attribute_type': 'Map:Person',
                'attribute_name': 'Person'
            }],
            'title': template_title,
            'audit': {
                'id': audit.id,
                'type': 'Audit'
            },
            'context': {
                'id': context.id
            },
        }
    }
    response = self.api.post(AssessmentTemplate, request_data)
    self.assertStatus(response, 201)

    template = all_models.AssessmentTemplate.query.filter_by(
        title=template_title).first()

    self.assertEqual(1, len(template.custom_attribute_definitions))
    self.assertEqual(lca_title, template.custom_attribute_definitions[0].title)
