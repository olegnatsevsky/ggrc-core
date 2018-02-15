# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""This module contains special query helper class for query API."""

import copy
import collections

from werkzeug.exceptions import Forbidden
from sqlalchemy import and_

from ggrc import db
from ggrc import models
from ggrc.utils import benchmark
from ggrc.rbac import permissions
from ggrc.query.default_handler import DefaultHandler


def _set_data(object_query, data):
  """Helper function for setting basic data in object_query"""
  object_query["count"] = len(data)
  object_query["total"] = len(data)
  object_query["last_modified"] = None
  object_query["values"] = data
  return object_query


# pylint: disable=too-few-public-methods
class AssessmentRelatedObjects(DefaultHandler):
  """Handler for assessment filter on my assessments page.

  Query filters with single relevant person and assessment statuses.

  """

  @classmethod
  def match(cls, query):
    """Check if the given query matches current handler."""
    if len(query) != 6:
      return False
    query = copy.deepcopy(query)

    assessment_ids = query[0]["filters"]["expression"]["ids"]
    if not isinstance(assessment_ids, list) or len(assessment_ids) != 1:
      return False
    expected = [{
        "object_name": "Snapshot",
        "filters": {
            "expression": {
                "object_name": "Assessment",
                "op": {"name": "relevant"},
                "ids": assessment_ids
            },
            "keys": [],
            "order_by":{"keys": [], "order":"", "compare":None}
        },
        "fields":[]
    }, {
        "object_name": "Comment",
        "filters": {
            "expression": {
                "object_name": "Assessment",
                "op": {"name": "relevant"},
                "ids": assessment_ids
            },
            "keys": [],
            "order_by":{"keys": [], "order":"", "compare":None
                        }
        },
        "order_by":[{"name": "created_at", "desc": True}],
        "fields": []
    }, {
        "object_name": "Evidence",
        "filters": {
            "expression": {
                "left": {
                    "object_name": "Assessment",
                    "op": {"name": "relevant"},
                    "ids": assessment_ids
                },
                "op": {"name": "AND"},
                "right": {
                    "left": "kind",
                    "op": {"name": "="},
                    "right": "FILE"
                }
            },
            "keys": [None]
        },
        "order_by":[{"name": "created_at", "desc": True}],
        "fields": []
    }, {
        "object_name": "Evidence",
        "filters": {
            "expression": {
                "left": {
                    "object_name": "Assessment",
                    "op": {"name": "relevant"},
                    "ids": assessment_ids
                },
                "op": {"name": "AND"},
                "right": {
                    "left": "kind",
                    "op": {"name": "="},
                    "right": "URL"
                }
            },
            "keys": [None]
        },
        "order_by":[{"name": "created_at", "desc": True}],
        "fields": []
    }, {
        "object_name": "Evidence",
        "filters": {
            "expression": {
                "left": {
                    "object_name": "Assessment",
                    "op": {"name": "relevant"},
                    "ids": assessment_ids
                },
                "op": {"name": "AND"},
                "right": {
                    "left": "kind",
                    "op": {"name": "="},
                    "right": "REFERENCE_URL"
                }
            },
            "keys": [None]
        },
        "fields":[],
        "order_by":[{"name": "created_at", "desc": True}]
    }, {
        "object_name": "Audit",
        "filters": {
            "expression": {
                "object_name": "Assessment",
                "op": {"name": "relevant"},
                "ids": assessment_ids
            },
            "keys": [],
            "order_by":{"keys": [], "order":"", "compare":None}
        },
        "limit":[0, 1],
        "fields":["id", "type", "title", "context"]
    }]
    return query == expected

  def _assessment(self):
    """Get the assessment used in the query and verify its permissions."""
    assessment_id = self.query[0]["filters"]["expression"]["ids"][0]
    assessment = models.Assessment.query.get(assessment_id)
    if permissions.is_allowed_read_for(assessment):
      return assessment
    raise Forbidden()

  def set_audit_result(self, assessment):
    """Set audit result"""
    object_query = self.query[5]
    data = db.session.query(
        models.Audit.id,
        models.Audit.title,
        models.Audit.context_id,
    ).filter(
        models.Audit.id == assessment.audit_id
    ).first()
    with benchmark("Get audit data"):
      object_query["count"] = 1
      object_query["total"] = 1
      object_query["last_modified"] = None
      object_query["values"] = [{
          "id": data.id,
          "title": data.title,
          "type": models.Audit.__name__,
          "context": {
              "context_id": None,
              "href": "/api/contexts/{}".format(data.context_id),
              "id": data.context_id,
              "type": "Context",
          },
      }]

  def set_snapshot_result(self, assessment):
    """Set snapshot result"""
    query = self.query[0]
    with benchmark("Get assessment snapshot relationships"):
      snapshots = db.session.query(
          models.Snapshot
      ).join(
          models.Relationship,
          and_(
              models.Snapshot.id == models.Relationship.source_id,
              models.Relationship.source_type == "Snapshot",
              models.Relationship.destination_id == assessment.id,
              models.Relationship.destination_type == "Assessment"
          )
      ).union(
          db.session.query(
              models.Snapshot
          ).join(
              models.Relationship,
              and_(
                  models.Snapshot.id == models.Relationship.destination_id,
                  models.Relationship.destination_type == "Snapshot",
                  models.Relationship.source_id == assessment.id,
                  models.Relationship.source_type == "Assessment"
              )
          )
      ).all()
    with benchmark("Set assessment snapshot relationships"):
      data = []
      for snapshot in snapshots:
        data.append({
            "archived": snapshot.archived,
            "revision": snapshot.revision.log_json(),
            "related_sources": [],
            "parent": {
                "context_id": assessment.context_id,
                "href": "/api/audits/{}".format(assessment.audit_id),
                "type": "Audit",
                "id": assessment.audit_id,
            },
            "child_type": snapshot.child_type,
            "child_id": snapshot.child_id,
            "related_destinations": [],
            "id": snapshot.id,
            "revisions": [],
            "revision_id": snapshot.revision_id,
            "type": snapshot.type,
        })

      _set_data(query, data)

  def set_comment_result(self, assessment):
    """Set comment result"""
    query = self.query[1]
    self.query[1]["last_modified"] = None
    with benchmark("Get assessment snapshot relationships"):
      comments = db.session.query(
          models.Comment
      ).join(
          models.Relationship,
          and_(
              models.Comment.id == models.Relationship.source_id,
              models.Relationship.source_type == "Comment",
              models.Relationship.destination_id == assessment.id,
              models.Relationship.destination_type == "Assessment"
          )
      ).union(
          db.session.query(
              models.Comment
          ).join(
              models.Relationship,
              and_(
                  models.Comment.id == models.Relationship.destination_id,
                  models.Relationship.destination_type == "Comment",
                  models.Relationship.source_id == assessment.id,
                  models.Relationship.source_type == "Assessment"
              )
          )
      ).all()
    with benchmark("Set assessment snapshot relationships"):
      data = []
      sorted_data = []
      for comment in comments:
        data.append(comment.log_json())
        sorted_data = sorted(data,
                             key=lambda x: (x["created_at"], x["id"]),
                             reverse=True)
      _set_data(query, sorted_data)

  def set_evidence_result(self, assessment):
    """Set evidence result"""
    data_map = collections.defaultdict(list)
    query_map = {
        models.Evidence.FILE: self.query[2],
        models.Evidence.URL: self.query[3],
        models.Evidence.REFERENCE_URL: self.query[4],
    }
    self.query[1]["last_modified"] = None
    with benchmark("Get assessment snapshot relationships"):
      evidences = db.session.query(
          models.Evidence
      ).join(
          models.Relationship,
          and_(
              models.Evidence.id == models.Relationship.source_id,
              models.Relationship.source_type == "Evidence",
              models.Relationship.destination_id == assessment.id,
              models.Relationship.destination_type == "Assessment"
          )
      ).union(
          db.session.query(
              models.Evidence
          ).join(
              models.Relationship,
              and_(
                  models.Evidence.id == models.Relationship.destination_id,
                  models.Relationship.destination_type == "Evidence",
                  models.Relationship.source_id == assessment.id,
                  models.Relationship.source_type == "Assessment"
              )
          )
      ).all()
    with benchmark("Set assessment snapshot relationships"):
      for evidence in evidences:
        data_map[evidence.kind].append(evidence.log_json())
      for kind, query in query_map.items():
        _set_data(query, data_map[kind])

  def get_results(self):
    """Filter the objects and get their information.

    Updates self.query items with their results. The type of results required
    is read from "type" parameter of every object_query in self.query.

    Returns:
      list of dicts: same query as the input with requested results that match
                     the filter.
    """
    assessment = self._assessment()

    self.set_snapshot_result(assessment)
    self.set_comment_result(assessment)
    self.set_evidence_result(assessment)
    self.set_audit_result(assessment)

    return self.query
