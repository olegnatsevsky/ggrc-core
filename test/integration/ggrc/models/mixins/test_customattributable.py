# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Integration test for custom attributable mixin"""
import collections
import ddt

from ggrc import db
from ggrc import models

from integration.ggrc import TestCase
from integration.ggrc.models import factories
from integration.ggrc import api_helper
from integration.ggrc.generator import ObjectGenerator


class TestCustomAttributableMixin(TestCase):

  """Test cases for functions in custom attributable mixin."""

  def test_setting_ca_values(self):
    """Test normal setting of custom attribute values."""
    with factories.single_commit():
      prog = factories.ProgramFactory()
      cad1 = factories.CustomAttributeDefinitionFactory(
          definition_type="program", title="CA 1", )
      cad2 = factories.CustomAttributeDefinitionFactory(
          definition_type="program", title="CA 2", )

    prog = prog.__class__.query.get(prog.id)

    val1 = models.CustomAttributeValue(
        attribute_value="55",
        custom_attribute=cad1,
    )
    val2 = models.CustomAttributeValue(
        attribute_value="129aaaaaa",
        custom_attribute=cad2,
    )

    prog.custom_attribute_values = [val1, val1, val1]
    db.session.commit()
    prog = prog.__class__.query.get(prog.id)
    self.assertEqual(len(prog.custom_attribute_values), 1)

    prog = factories.ProgramFactory()
    prog.custom_attribute_values.append(val1)
    db.session.commit()
    prog = prog.__class__.query.get(prog.id)
    self.assertEqual(len(prog.custom_attribute_values), 1)
    self.assertEqual(
        {"55"},
        set(v.attribute_value for v in prog.custom_attribute_values),
    )

    prog = factories.ProgramFactory()
    prog.custom_attribute_values = [val1, val2]
    db.session.commit()
    prog = prog.__class__.query.get(prog.id)

    self.assertEqual(
        {"55", "129aaaaaa"},
        set(v.attribute_value for v in prog.custom_attribute_values),
    )
    self.assertEqual(len(prog.custom_attribute_values), 2)

  def test_updating_ca_values(self):
    """Test updating custom attribute values."""
    cad1 = factories.CustomAttributeDefinitionFactory(
        definition_type="program",
        title="CA 1",
    )
    val1 = models.CustomAttributeValue(
        attribute_value="55",
        custom_attribute=cad1,
    )
    prog = factories.ProgramFactory()
    prog.custom_attribute_values = [val1]
    db.session.commit()

    prog = prog.__class__.query.get(prog.id)
    self.assertEqual(prog.custom_attribute_values[0].attribute_value, "55")

    val2 = models.CustomAttributeValue(
        attribute_value="129",
        custom_attribute=cad1,
    )

    prog.custom_attribute_values = [val2]
    db.session.commit()

    prog = prog.__class__.query.get(prog.id)
    self.assertEqual(prog.custom_attribute_values[0].attribute_value, "129")

  def test_validate_text_ca_value(self):
    """Test validator for Text CA value."""
    generator = ObjectGenerator()
    prog = factories.ProgramFactory()
    cad1 = factories.CustomAttributeDefinitionFactory(
        definition_type="program",
        definition_id=prog.id,
        attribute_type="Text",
        title="CA 1",
    )
    val1 = factories.CustomAttributeValueFactory(
        attributable=prog,
        attribute_value=" http://www.some.url",
        custom_attribute=cad1,
    )
    prog.custom_attribute_values = [val1]
    generator.api.modify_object(prog, {})

    prog = prog.__class__.query.get(prog.id)
    self.assertEqual(prog.custom_attribute_values[0].attribute_value,
                     "http://www.some.url")

  def test_ca_setattr(self):
    """Test setting custom attribute values with setattr."""
    with factories.single_commit():
      prog = factories.ProgramFactory()
      cad1 = factories.CustomAttributeDefinitionFactory(
          definition_type="program",
          title="CA 1",
      )

    setattr(prog, "custom_attribute_values", [{
            "attribute_value": "55",
            "custom_attribute_id": cad1.id,
            }])
    db.session.commit()
    prog = prog.__class__.query.get(prog.id)

    self.assertEqual(
        {"55"},
        set(v.attribute_value for v in prog.custom_attribute_values),
    )
    self.assertEqual(len(prog.custom_attribute_values), 1)

  def test_setting_ca_dict(self):
    """Test setting custom attribute values dict."""
    with factories.single_commit():
      prog = factories.ProgramFactory()
      cad1 = factories.CustomAttributeDefinitionFactory(
          definition_type="program",
          title="CA 1", )
      cad2 = factories.CustomAttributeDefinitionFactory(
          definition_type="program",
          title="CA 2",
      )

    prog.custom_attribute_values = [
        {
            "attribute_value": "55",
            "custom_attribute_id": cad1.id,
        }, {
            "attribute_value": "129aaaaaa",
            "custom_attribute_id": cad2.id,
        }
    ]
    db.session.commit()
    prog = prog.__class__.query.get(prog.id)

    self.assertEqual(
        {"55", "129aaaaaa"},
        set(v.attribute_value for v in prog.custom_attribute_values),
    )
    self.assertEqual(len(prog.custom_attribute_values), 2)

  def test_updating_ca_dict(self):
    """Test updating custom attribute values with a dict."""
    with factories.single_commit():
      prog = factories.ProgramFactory()
      cad1 = factories.CustomAttributeDefinitionFactory(
          definition_type="program",
          title="CA 1",
      )

    prog.custom_attribute_values = [{
        "attribute_value": "55",
        "custom_attribute_id": cad1.id,
    }]
    db.session.commit()
    prog = prog.__class__.query.get(prog.id)

    prog.custom_attribute_values = [{
        "attribute_value": "57",
        "custom_attribute_id": cad1.id,
    }]

    self.assertEqual(len(prog.custom_attribute_values), 1)
    self.assertEqual(prog.custom_attribute_values[0].attribute_value, "57")

  def test_adding_bad_ca_dict(self):
    """Test setting invalid custom attribute values."""
    with factories.single_commit():
      prog = factories.ProgramFactory()
      cad1 = factories.CustomAttributeDefinitionFactory(
          definition_type="section",
          title="CA 1",
      )

    with self.assertRaises(ValueError):
      prog.custom_attribute_values = [{
          "attribute_value": "55",
          "custom_attribute_id": -1
      }]
      prog.validate_custom_attributes()

    with self.assertRaises(ValueError):
      prog.custom_attribute_values = [{
          "attribute_value": "55",
          "custom_attribute_id": cad1.id,
      }]
      prog.validate_custom_attributes()

  def test_adding_mapping_ca_dict(self):
    """Test adding mapping custom attribute values with a dict."""
    with factories.single_commit():
      assessment = factories.AssessmentFactory()
      db.session.flush()  # to make sure assessment.id is set
      cad1 = factories.CustomAttributeDefinitionFactory(
          definition_type="assessment",
          attribute_type="Map:Person",
          title="CA 1",
          definition_id=assessment.id
      )
      cad2 = factories.CustomAttributeDefinitionFactory(
          definition_type="assessment",
          attribute_type="Map:Person",
          title="CA 2",
          definition_id=assessment.id
      )

    assessment.custom_attribute_values = [
        {
            "attribute_value": "Person:1",
            "custom_attribute_id": cad1.id,
        }, {
            "attribute_value": "Person",
            "attribute_object_id": "1",
            "custom_attribute_id": cad2.id,
        }
    ]
    assessment.validate_custom_attributes()
    assessment = assessment.__class__.query.get(assessment.id)
    self.assertEqual(
        {"1"},
        set(v.attribute_object_id for v in assessment.custom_attribute_values),
    )
    self.assertEqual(
        {"Person"},
        set(v.attribute_value for v in assessment.custom_attribute_values),
    )
    self.assertEqual(len(assessment.custom_attribute_values), 2)


@ddt.ddt
class TestCreateRevisionAfterDeleteCAD(TestCase):
  """Test cases for creating new revision after delete CAD"""
  def setUp(self):
    self.api_helper = api_helper.Api()

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

    self.api_helper.delete(cad)

    snapshot = models.Snapshot.query.filter().first()

    self.assertEqual(snapshot.is_latest_revision, False)


class TestCADUpdate(TestCase):
  """Test cases for updating model inherited custom attributable mixin."""
  def setUp(self):
    """Set up test cases."""
    super(TestCADUpdate, self).setUp()
    self.client.get("/login")
    self.api = api_helper.Api()

  def test_lcads_removing(self):
    """Test removing of LCADs from AssessmentTemplate"""
    with factories.single_commit():
      template = factories.AssessmentTemplateFactory()
      for i in range(2):
        factories.CustomAttributeDefinitionFactory(
            title="test CA def {}".format(i),
            definition_type=template._inflector.table_singular,
            definition_id=template.id,
            attribute_type="Text"
        )

    response = self.api.put(template, {"custom_attribute_definitions": []})
    self.assert200(response)

    cads_query = models.CustomAttributeDefinition.query.filter_by(
        definition_type=template._inflector.table_singular,
        definition_id=template.id,
    )
    self.assertEqual(cads_query.count(), 0)

  def test_lcads_import_update(self):
    """Test saving of LCADs for Assessment Template after import"""
    cads_count = 2
    with factories.single_commit():
      template = factories.AssessmentTemplateFactory()
      for i in range(cads_count):
        factories.CustomAttributeDefinitionFactory(
            title="test CA def {}".format(i),
            definition_type=template._inflector.table_singular,
            definition_id=template.id,
            attribute_type="Text"
        )
    response = self.import_data(collections.OrderedDict([
        ("object_type", "Assessment_Template"),
        ("Code*", template.slug),
        ("Title", "New title"),
    ]))
    self._check_csv_response(response, {})

    cads_query = models.CustomAttributeDefinition.query.filter_by(
        definition_type=template._inflector.table_singular,
        definition_id=template.id,
    )
    self.assertEqual(cads_query.count(), cads_count)
