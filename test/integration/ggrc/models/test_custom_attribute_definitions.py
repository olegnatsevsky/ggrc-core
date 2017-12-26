# Copyright (C) 2017 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Integration test for CustomAttributeDefinition"""
import ddt

from ggrc import db
from ggrc.models import exceptions
from integration import ggrc
from integration.ggrc.models import factories


@ddt.ddt
class TestCustomAttributeDefinition(ggrc.TestCase):
  """Test case for CustomAttributeDefinition"""
  def setUp(self):
    super(TestCustomAttributeDefinition, self).setUp()
    self.client.get("/login")

  @ddt.data(
      'access_group',
      'assessment',
      'clause',
      'contract',
      'control',
      'data_asset',
      'facility',
      'issue',
      'market',
      'objective',
      'org_group',
      'policy',
      'product',
      'program',
      'project',
      'regulation',
      'risk',
      'section',
      'standard',
      'system',
      'threat',
      'vendor',
  )
  def test_gca_map_person(self, def_type):
    """GCA with Person type is not allowed for object of type {0}. """
    with self.assertRaises(exceptions.ValidationError):
      factories.CustomAttributeDefinitionFactory(definition_type=def_type,
                                                 attribute_type='Map:Person',
                                                 title='map_person_gca',
                                                 )

  def test_lca_map_person(self):
    """LCA with Person type is allowed."""
    with factories.single_commit():
      audit = factories.AuditFactory()
      assessment = factories.AssessmentFactory(audit=audit)
      factories.RelationshipFactory(source=audit, destination=assessment)
      person = factories.PersonFactory()
      db.session.flush()  # to make sure assessment.id, person.id is set

      cad = factories.CustomAttributeDefinitionFactory(
          definition_id=assessment.id,
          definition_type='assessment',
          attribute_type='Map:Person',
          title='map_person_lca'
      )
    assessment.custom_attribute_values = [{
        'attribute_value': 'Person',
        'attribute_object_id': person.id,
        'custom_attribute_id': cad.id,
    }]
    assessment = self.refresh_object(assessment)
    first_custom_attr = assessment.custom_attribute_values[0]
    self.assertEqual(first_custom_attr.attribute_object_id, person.id)
