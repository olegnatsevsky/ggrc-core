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
class TestDocumentQueries(TestCase):
  """Tests for /query api for Document instance filtering."""

  def setUp(self):
    super(TestDocumentQueries, self).setUp()
    self.api = Api()

  @ddt.data(all_models.Document.ATTACHMENT, all_models.Document.URL)
  def test_filter_document_by_type(self, document_type):
    """Test filter documents by document type."""
    data = {
        all_models.Document.ATTACHMENT: factories.EvidenceTypeDocumentFactory().id,
        all_models.Document.URL: factories.UrlFactory().id,
    }
    query_request_data = [{
        u'fields': [],
        u'filters': {
            u'expression': {
                u'left': u'document_type',
                u'op': {u'name': u'='},
                u'right': document_type,
            }
        },
        u'limit': [0, 5],
        u'object_name': u'Document',
        u'permissions': u'read',
        u'type': u'values',
    }]
    resp = self.api.send_request(self.api.client.post,
                                 data=query_request_data,
                                 api_link="/query")
    self.assertEqual(1, resp.json[0]["Document"]["count"])
    self.assertEqual(data[document_type],
                     resp.json[0]["Document"]["values"][0]["id"])
