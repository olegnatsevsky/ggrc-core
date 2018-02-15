# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Integration tests for Document"""
from mock import mock

from werkzeug.exceptions import Unauthorized

from ggrc.gdrive import GdriveUnauthorized
from ggrc.models import all_models
from ggrc.models import exceptions
from integration.ggrc import TestCase
from integration.ggrc.api_helper import Api
from integration.ggrc import generator
from integration.ggrc.models import factories


# pylint: disable=unused-argument
def dummy_gdrive_response(*args, **kwargs):  # noqa
  return {'webViewLink': 'http://mega.doc',
          'name': 'test_name',
          'id': '1234567'}


class TestDocument(TestCase):
  """Document test cases"""
  # pylint: disable=invalid-name

  def setUp(self):
    super(TestDocument, self).setUp()
    self.api = Api()
    self.gen = generator.ObjectGenerator()

  def test_get_parent_obj_control_type(self):
    """Test mapping parent of Control type"""
    control = factories.ControlFactory()
    document = factories.EvidenceTypeDocumentFactory(
        parent_obj={
            'id': control.id,
            'type': 'Control'
        })
    expected_control = document.related_objects(_types=[control.type]).pop()
    self.assertEqual(expected_control, control)

  def test_parent_obj_validation_is_id_presents(self):
    """Validation parent_obj id should present."""
    with self.assertRaises(exceptions.ValidationError):
      factories.EvidenceTypeDocumentFactory(
          parent_obj={
              'type': 'Control'
          })

  def test_parent_obj_validation_is_type_presents(self):
    """Validation parent_obj type should present."""
    control = factories.ControlFactory()
    with self.assertRaises(exceptions.ValidationError):
      factories.EvidenceTypeDocumentFactory(
          parent_obj={
              'id': control.id
          })

  def test_parent_obj_validation_wrong_type(self):
    """Validation parent_obj type.

    Type should be in 'Control', 'Issue', 'RiskAssessment'.
    """
    control = factories.ControlFactory()
    with self.assertRaises(exceptions.ValidationError):
      factories.EvidenceTypeDocumentFactory(
          parent_obj={
              'id': control.id,
              'type': 'Program'
          })

  def test_documentable_postfix_one_control(self):
    """Test documentable postfix for assessment with one control."""

    control = factories.ControlFactory()
    document = factories.EvidenceTypeDocumentFactory(
        parent_obj={
            'id': control.id,
            'type': 'Control'
        })

    expected = '_ggrc_control-{}'.format(control.id)
    # pylint: disable=protected-access
    result = document._build_file_name_postfix(control)
    self.assertEqual(expected, result)


  @mock.patch('ggrc.gdrive.file_actions.process_gdrive_file',
              dummy_gdrive_response)
  def test_copy_document(self):
    """Test copy document."""
    control = factories.ControlFactory()
    factories.EvidenceTypeDocumentFactory(
        source_gdrive_id='test_gdrive_id',
        parent_obj={
            'id': control.id,
            'type': 'Control'
        })
    self.assertEqual(len(control.documents), 1)

    # data from dummy_gdrive_response
    self.assertEqual(control.documents_file[0].title, 'test_name')
    self.assertEqual(control.documents_file[0].gdrive_id, '1234567')

  def test_rename_document(self):
    """Test rename document."""
    with mock.patch('ggrc.gdrive.file_actions.process_gdrive_file') as mocked:
      mocked.return_value = {
          'webViewLink': 'http://mega.doc',
          'name': 'new_name',
          'id': '1234567'
      }
      control = factories.ControlFactory()
      factories.EvidenceTypeDocumentFactory(
          is_uploaded=True,
          source_gdrive_id='some link',
          parent_obj={
              'id': control.id,
              'type': 'Control'
          })
      folder_id = ''
      mocked.assert_called_with(folder_id, 'some link',
                                '_ggrc_control-{}'.format(control.id),
                                is_uploaded=True,
                                separator='_ggrc')
      self.assertEqual(len(control.documents), 1)
      self.assertEqual(control.documents_file[0].title, 'new_name')

  def test_update_title(self):
    """Test update document title."""
    create_title = "test_title"
    update_title = "update_test_title"
    document = factories.DocumentFactory(title=create_title)
    response = self.api.put(document, {"title": update_title})
    self.assert200(response)
    self.assertEqual(all_models.Document.query.get(document.id).title,
                     update_title)

  def create_document_by_type(self, kind):
    """Create document with sent type."""
    data = {
        "title": "test_title",
        "link": "test_link",
    }
    if kind is not None:
      data["kind"] = kind
    kind = kind or all_models.Document.URL
    resp, doc = self.gen.generate_object(
        all_models.Document,
        data
    )
    self.assertTrue(
        all_models.Document.query.filter(
            all_models.Document.id == resp.json["document"]["id"],
            all_models.Document.kind == kind,
        ).all()
    )
    return (resp, doc)

  def test_create_url(self):
    """Test create url."""
    self.create_document_by_type(all_models.Document.URL)

  def test_create_url_default(self):
    """Test create url(default)."""
    self.create_document_by_type(None)

  def test_create_evidence(self):
    """Test create evidence."""
    self.create_document_by_type(all_models.Document.FILE)

  def test_create_invalid_type(self):
    """Test validation document_type."""
    data = {
        "kind": 3,
        "title": "test_title",
        "link": "test_link",
        "owners": [self.gen.create_stub(all_models.Person.query.first())],
    }
    obj_name = all_models.Document._inflector.table_singular
    obj = all_models.Document()
    obj_dict = self.gen.obj_to_dict(obj, obj_name)
    obj_dict[obj_name].update(data)
    resp = self.api.post(all_models.Document, obj_dict)
    self.assert400(resp)
    self.assertEqual('"Invalid value for attribute kind. '
                     'Expected options are `URL`, `FILE`, '
                     '`REFERENCE_URL`"',
                     resp.data)

  def test_header_on_expected_error(self):
    """During authorization flow we have the expected 'Unauthorized'.

    To allow FE ignore the error popup we need to set
    'X-Expected-Error' header
    """
    # pylint: disable=unused-argument
    def side_effect_function(*args, **kwargs):
      raise GdriveUnauthorized("Unable to get valid credentials")

    with mock.patch("ggrc.gdrive.file_actions.process_gdrive_file") as mocked:
      mocked.side_effect = side_effect_function
      control = factories.ControlFactory()
      response = self.api.post(all_models.Document, [{
          "document": {
              "kind": all_models.Document.FILE,
              "source_gdrive_id": "some link",
              "link": "some link",
              "title": "some title",
              "context": None,
              "parent_obj": {
                  "id": control.id,
                  "type": "Control"
              }
          }
      }])
    self.assertEqual(response.status_code, 401)
    self.assertIn('X-Expected-Error', response.headers)

  def test_header_on_unexpected_error(self):
    """During authorization flow we have the expected 'Unauthorized'.

    If error is unexpected we need to make sure that 'X-Expected-Error'
    header is not set.
    """
    # pylint: disable=unused-argument
    def side_effect_function(*args, **kwargs):
      raise Unauthorized("Unable to get valid credentials")

    with mock.patch("ggrc.gdrive.file_actions.process_gdrive_file") as mocked:
      mocked.side_effect = side_effect_function
      control = factories.ControlFactory()
      response = self.api.post(all_models.Document, [{
          "document": {
              "kind": all_models.Document.FILE,
              "source_gdrive_id": "some link",
              "link": "some link",
              "title": "some title",
              "context": None,
              "parent_obj": {
                  "id": control.id,
                  "type": "Control"
              }
          }
      }])
    self.assertEqual(response.status_code, 401)
    self.assertNotIn('X-Expected-Error', response.headers)

  def test_header_on_expected_error_batch(self):
    """During authorization flow we have the expected 'Unauthorized'.

    To allow FE ignore popup we need to set 'X-Expected-Error' header
    """
    # pylint: disable=unused-argument
    def side_effect_function(*args, **kwargs):
      raise GdriveUnauthorized("Unable to get valid credentials")

    with mock.patch("ggrc.gdrive.file_actions.process_gdrive_file") as mocked:
      mocked.side_effect = side_effect_function
      control = factories.ControlFactory()

      doc1 = {
          "document": {
              "kind": all_models.Document.FILE,
              "source_gdrive_id": "some link",
              "link": "some link",
              "title": "some title",
              "context": None,
              "parent_obj": {
                  "id": control.id,
                  "type": "Control"
              }
          }
      }
      doc2 = {
          "document": {
              "kind": all_models.Document.URL,
              "link": "some link",
              "title": "some title",
              "context": None,
          }
      }

    response = self.api.post(all_models.Document, [doc1, doc2])
    self.assertEqual(response.status_code, 401)
    self.assertIn('X-Expected-Error', response.headers)

  def create_document_by_api(self, kind=all_models.Document.URL):
    document_data = dict(
        title='Simple title',
        kind=kind,
        link='some_url.com',
        description='mega description'
    )
    _, document = self.gen.generate_object(
        all_models.Document,
        document_data
    )

    result = all_models.Document.query.filter(
        all_models.Document.id == document.id).one()

    self.assertEqual(result.title, 'Simple title')
    self.assertEqual(result.kind, kind)
    self.assertEqual(result.link, 'some_url.com')
    self.assertEqual(result.description, 'mega description')

  def test_document_url_type_with_parent(self):
    """Document of URL type should mapped to parent if parent specified"""
    control = factories.ControlFactory()
    document = factories.UrlTypeDocumentFactory(
        description='mega description',
        parent_obj={
            'id': control.id,
            'type': 'Control'
        }
    )
    rel_evidences = control.related_objects(_types=[document.type])
    self.assertEqual(document, rel_evidences.pop())
