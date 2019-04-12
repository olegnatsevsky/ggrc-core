# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Simple api client to simulate external app requests"""

import json

from ggrc.app import app


class ExternalApiClient(object):
  """Simulates requests from external_app"""

  DEFAULT_HEADERS = {
      "X-ggrc-user": json.dumps({
          "email": "external_app@example.com"
      }),
      "X-Requested-By": "SYNC_SERVICE",
      "Content-Type": "application/json",
      "X-URLFetch-Service-Id": "GOOGLEPLEX",
  }

  def __init__(self):
    self.client = app.test_client()
    self.user_headers = {}

  def _build_headers(self):
    """Builds ext_app specific headers"""
    headers = self.DEFAULT_HEADERS.copy()
    headers.update(self.user_headers)
    return headers

  def get(self, obj=None, obj_id=None, url=None):
    """Simulates ext_app GET request"""
    if not url:
      obj_type = self._get_object_type(obj)
      url = self._build_api_link(obj_type, obj_id)
    headers = self._build_headers()
    return self.client.get(url, headers=headers)

  @staticmethod
  def _get_object_type(obj):
    if isinstance(obj, basestring):
      obj_type = obj
    elif hasattr(obj, "_inflector"):
      obj_type = obj._inflector.table_singular
    else:
      raise ValueError("Unknown object type: {}".format(type(obj)))
    return obj_type

  def post(self, obj=None, url=None, data=None):
    """Simulates ext_app POST request"""
    if not url:
      obj_type = self._get_object_type(obj)
      url = self._build_api_link(obj_type)
    headers = self._build_headers()
    assert (isinstance(data, dict) or
            isinstance(data, list)), "'data' must be in dict or list"
    return self.client.post(url, data=json.dumps(data), headers=headers)

  def put(self, obj=None, obj_id=None, data=None,
          load_precondition_headers=False):
    """Simulates ext_app PUT request

    Default behavior is not use precondition headers:
     - "If-Match"
     - "If-Unmodified-Since"
    same as sync service does.

    if we need to simulate old-style mechanism (as GGRCQ does) we need to set
    load_precondition_headers = True
    """

    obj_type = self._get_object_type(obj)
    assert obj_id, "obj_id is mandatory for PUT request"
    assert data, "data is mandatory for PUT request"

    url = self._build_api_link(obj_type, obj_id)
    headers = self._build_headers()

    resp = self.get(obj_type, obj_id)
    if load_precondition_headers:
      precondition_headers = {
          "If-Match": resp.headers.get("Etag"),
          "If-Unmodified-Since": resp.headers.get("Last-Modified")
      }
      headers.update(precondition_headers)

    if obj_type not in data:
      resp.json[obj_type].update(data)
      data = resp.json

    return self.client.put(url, data=json.dumps(data), headers=headers)

  def _get_precondition_headers(self, obj_type, obj_id):
    """To perform DELETE/PUT client needs specific headers

    To build such headers we need to issue GET request.
    """
    resp = self.get(obj_type, obj_id)
    precondition_headers = {
        "If-Match": resp.headers.get("Etag"),
        "If-Unmodified-Since": resp.headers.get("Last-Modified")
    }
    return precondition_headers

  @staticmethod
  def _build_api_link(obj_type, obj_id=None):
    """Build api link based on obj_type and obj_id"""
    obj_id_part = "" if obj_id is None else "/" + str(obj_id)
    return "/api/{}s{}".format(obj_type, obj_id_part)

  def delete(self, obj, obj_id, url=None):
    """Simulates ext_app DELETE request"""
    obj_type = self._get_object_type(obj)
    if not url:
      url = self._build_api_link(obj_type, obj_id)

    headers = self._build_headers()
    precondition_headers = self._get_precondition_headers(obj_type, obj_id)

    headers.update(precondition_headers)
    return self.client.delete(url, headers=headers)
