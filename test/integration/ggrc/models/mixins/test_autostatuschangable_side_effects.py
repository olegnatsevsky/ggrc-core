import collections

import ddt

from ggrc import models
from integration.ggrc.models import factories
from integration.ggrc.models.mixins import test_autostatuschangable as asc


@ddt.ddt
class TestSideEffects(asc.TestMixinAutoStatusChangeableBase):
  """Test case for AutoStatusChangeable side effects.

  After the implementation of new AutoStatusChangeable rules, we have
  few sensitive side effects during import and some other situations. The goal
  of this test is to explain this behaviour.
  """

  # pylint: disable=invalid-name
  @ddt.data(
      (models.Assessment.DONE_STATE, models.Assessment.PROGRESS_STATE),
      (models.Assessment.FINAL_STATE, models.Assessment.PROGRESS_STATE),
      (models.Assessment.START_STATE, models.Assessment.START_STATE),
      (models.Assessment.REWORK_NEEDED, models.Assessment.REWORK_NEEDED),
  )
  @ddt.unpack
  def test_assessments_import_update(self, from_status, expected_status):
    """Test for updating Assessment with import.

    If we update some attribute during import like 'Notes',
    autostatuschangeable mixin overrides imported status.
    """

    audit = factories.AuditFactory()
    slug = "TestAssessment"
    self.import_data(collections.OrderedDict([
      ("object_type", "Assessment"),
      ("Code*", slug),
      ("Audit*", audit.slug),
      ("Assignees*", "test@email.com"),
      ("Creators", "test@email.com"),
      ("Title", "Test assessment"),
      ("Notes", "some notes"),
      ("State*", from_status),
    ]))

    self.import_data(collections.OrderedDict([
      ("object_type", "Assessment"),
      ("Code*", slug),
      ("Audit*", audit.slug),
      ("Assignees*", "test@email.com"),
      ("Creators", "test@email.com"),
      ("Title", "Test assessment"),
      ("Notes", "some new notes"),
      ("State*", from_status),
    ]))

    assessment = models.Assessment.query.filter(
      models.Assessment.slug == slug
    ).first()

    self.assertEqual(expected_status, assessment.status)

  @ddt.data(
    (models.Assessment.DONE_STATE, models.Assessment.PROGRESS_STATE),
    (models.Assessment.FINAL_STATE, models.Assessment.PROGRESS_STATE),
    (models.Assessment.START_STATE, models.Assessment.START_STATE),
    (models.Assessment.REWORK_NEEDED, models.Assessment.REWORK_NEEDED),
  )
  @ddt.unpack
  def test_assessments_update_status_one_put(self, from_status,
                                             expected_status):
    """Test for updating Assessment with new status in the same PUT.

    We can update some assessment's attribute and the status in the same PUT,
    autostatuschangeable mixin overrides this status.
    """

    with factories.single_commit():
      ca_factory = factories.CustomAttributeDefinitionFactory
      gca = ca_factory(definition_type='assessment',
                       title='rich_test_gca',
                       attribute_type='Rich Text'
                       )
      assessment = factories.AssessmentFactory()
    self.api.modify_object(assessment, {
        'custom_attribute_values': [{
            'custom_attribute_id': gca.id,
            'attribute_value': 'some value',
        }],
        'status': from_status
    })
    assessment = self.refresh_object(assessment)
    self.assertEqual(expected_status, assessment.status)
