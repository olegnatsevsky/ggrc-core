# coding: utf-8

# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Tests for /query api endpoint."""

import ddt

from ggrc.models import all_models

from integration.ggrc import TestCase
from integration.ggrc.api_helper import Api
from integration.ggrc.models import factories


@ddt.ddt
class TestEvidenceQueries(TestCase):
  """Tests for /query api for Evidence instance filtering."""

  def setUp(self):
    super(TestEvidenceQueries, self).setUp()
    self.api = Api()

  def test_filter_evidence_by_type_url(self):
    """Test filter evidences by evidence type URL."""
    evidence_gdrive = factories.EvidenceFactory(
      title='Simple title',
      kind=all_models.Evidence.URL,
      link='sample.site'
    )
    evidence_url_id = evidence_gdrive.id

    query_request_data = [{
      u'filters': {
        u'expression': {
          u'left': u'kind',
          u'op': {u'name': u'='},
          u'right': all_models.Evidence.URL,
        }
      },
      u'object_name': u'Evidence',
      u'type': u'values',
    }]
    resp = self.api.send_request(self.api.client.post,
                                 data=query_request_data,
                                 api_link="/query")
    self.assertEqual(1, resp.json[0]["Evidence"]["count"])
    self.assertEqual(evidence_url_id,
                     resp.json[0]["Evidence"]["values"][0]["id"])

  def test_filter_evidence_by_type_gdrive(self):
    """Test filter evidences by evidence type GDRIVE."""
    evidence_gdrive = factories.EvidenceFactory(
      title='Simple title',
      source_gdrive_id='gdrive_id',
      link='sample.site',
      kind=all_models.Evidence.FILE,
    )
    evidence_gdrive_id = evidence_gdrive.id
    query_request_data = [{
      u'filters': {
        u'expression': {
          u'left': u'kind',
          u'op': {u'name': u'='},
          u'right': all_models.Evidence.FILE,
        }
      },
      u'object_name': u'Evidence',
      u'type': u'values',
    }]
    resp = self.api.send_request(self.api.client.post,
                                 data=query_request_data,
                                 api_link="/query")
    self.assertEqual(1, resp.json[0]["Evidence"]["count"])
    self.assertEqual(evidence_gdrive_id,
                     resp.json[0]["Evidence"]["values"][0]["id"])
