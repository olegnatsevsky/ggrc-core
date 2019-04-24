# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Integration test for custom attributable mixin"""
import ddt

from ggrc import models

from integration.ggrc import TestCase
from integration.ggrc.external_app.external_api_helper import ExternalApiClient
from integration.ggrc.models import factories


@ddt.ddt
class TestCreateRevisionAfterDeleteCAD(TestCase):
  """Test cases for creating new revision after delete CAD"""
  def setUp(self):
    super(TestCreateRevisionAfterDeleteCAD, self).setUp()
    self.ext_api = ExternalApiClient()
  @ddt.data(True, False)
  def test_latest_revision_delete_cad(self, is_add_cav):
    """Test creating new revision after deleting CAD.

    In case of deleting CAD, snapshot attribute is_latest_revision
    must be False
    """
    with factories.single_commit():
      control = factories.ControlFactory()
      program = factories.ProgramFactory()
      factories.RelationshipFactory(
          source=program,
          destination=control,
      )

      audit = factories.AuditFactory()

      factories.RelationshipFactory(
          source=audit,
          destination=control
      )
      cad = factories.CustomAttributeDefinitionFactory(
          title="test_name",
          definition_type="control",
          attribute_type="Text",
      )

      if is_add_cav:
        factories.CustomAttributeValueFactory(
            custom_attribute=cad,
            attributable=control,
            attribute_value="test",
        )

      last_revision = models.Revision.query.filter(
          models.Revision.resource_id == control.id,
          models.Revision.resource_type == control.type,
      ).order_by(models.Revision.id.desc()).first()

      snapshot = factories.SnapshotFactory(
          parent=audit,
          child_id=control.id,
          child_type=control.type,
          revision=last_revision,
      )

    self.assertTrue(snapshot.is_latest_revision)

    self.ext_api.delete(cad, cad.id)

    snapshot = models.Snapshot.query.filter().first()

    self.assertEqual(snapshot.is_latest_revision, False)
