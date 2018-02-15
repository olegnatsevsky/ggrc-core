from mock import mock

from ggrc.models import all_models
from integration.ggrc import TestCase
from integration.ggrc.models import factories

COPIED_TITLE = 'test_name'


def dummy_gdrive_response(*args, **kwargs):  # noqa
  return {'webViewLink': 'http://mega.doc',
          'name': COPIED_TITLE}


class TestWithEvidence(TestCase):

  @mock.patch('ggrc.gdrive.file_actions.process_gdrive_file', dummy_gdrive_response)
  def test_evidences(self):
    """Test related evidences"""

    audit = factories.AuditFactory()
    factories.EvidenceFactory(
      title='Simple title',
      kind=all_models.Evidence.FILE,
      source_gdrive_id='123',
      parent_obj={
        'id': audit.id,
        'type': audit.type
      })

    self.assertEqual(len(audit.evidences), 1)
    self.assertEqual(audit.evidences[0].title, COPIED_TITLE)

  @mock.patch('ggrc.gdrive.file_actions.process_gdrive_file', dummy_gdrive_response)
  def test_evidevce_type(self):
    """Test related evidences"""

    audit = factories.AuditFactory()
    factories.EvidenceFactory(
      title='Simple title1',
      kind=all_models.Evidence.FILE,
      source_gdrive_id='123',
      parent_obj={
        'id': audit.id,
        'type': audit.type
      })

    factories.EvidenceFactory(
      title='Simple title2',
      kind=all_models.Evidence.URL,
      source_gdrive_id='123',
      parent_obj={
        'id': audit.id,
        'type': audit.type
      })

    self.assertEqual(len(audit.evidences), 2)
    self.assertEqual(len(audit.evidences_url), 1)
    self.assertEqual(len(audit.evidences_file), 1)
