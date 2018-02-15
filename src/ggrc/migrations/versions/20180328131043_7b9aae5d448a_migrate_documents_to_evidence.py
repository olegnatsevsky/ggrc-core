# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
Migrate documents to evidence

Create Date: 2018-03-28 13:10:43.600584
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name
import json

import datetime
from collections import namedtuple

from sqlalchemy.sql import text
from alembic import op


# revision identifiers, used by Alembic.
from ggrc.migrations.utils.migrator import get_migration_user_id

revision = '7b9aae5d448a'
down_revision = '207955a2d3c1'

Evidence = namedtuple('Evidence', 'kind, description, title, context_id, '
                                  'source_gdrive_id, slug, link, id, gdrive_id')


def last_insert_id(connection):
  return connection.execute(text('select LAST_INSERT_ID()')).fetchone()[0]


def get_docs_to_migrate(connection):
  sql = """
  SELECT
    d.id as doc_id, d.modified_by_id, d.title, d.link,
    d.description, d.context_id, d.source_gdrive_id,
    d.gdrive_id, d.kind, r.id as rel_id,
    r.source_id as counterparty_id,
    r.source_type as counterparty_type
  FROM
    documents as d
  JOIN relationships as r
    ON r.destination_id = d.id
  WHERE
    r.destination_type = 'Document' AND
    d.kind in ('FILE', 'URL') AND
    r.source_type in ('Audit', 'Assessment')
  UNION ALL
  SELECT
    d.id as doc_id, d.modified_by_id, d.title, d.link,
    d.description, d.context_id, d.source_gdrive_id, d.gdrive_id,
    d.kind, r.id as rel_id,
    r.destination_id as counterparty_id,
    r.destination_type as counterparty_type
  FROM
    documents as d
  JOIN relationships as r
    ON r.source_id = d.id
  WHERE
    r.source_type = 'Document' AND
    d.kind in ('FILE', 'URL') AND
    r.destination_type in ('Audit', 'Assessment')
  """
  return connection.execute(text(sql))


def create_evidence(connection, doc):
  sql = """
      INSERT INTO evidence (
        modified_by_id,
        created_at,
        updated_at,
        title,
        link,
        description,
        context_id,
        kind,
        source_gdrive_id,
        gdrive_id)
      VALUES (:modified_by_id, NOW(), NOW(), :title, :link,
              :description, :context_id, :kind, :source_gdrive_id, :gdrive_id)
      """
  connection.execute(text(sql),
                     modified_by_id=doc.modified_by_id,
                     title=doc.title,
                     link=doc.link,
                     description=doc.description,
                     context_id=doc.context_id,
                     kind=doc.kind,
                     source_gdrive_id=doc.source_gdrive_id,
                     gdrive_id=doc.gdrive_id)

  evidence_id = last_insert_id(connection)
  slug = 'EVIDENCE-{}'.format(evidence_id)
  set_evidence_slug(connection, evidence_id, slug)

  return Evidence(
    title=doc.title,
    link=doc.link,
    description=doc.description,
    context_id=doc.context_id,
    kind=doc.kind,
    source_gdrive_id=doc.source_gdrive_id,
    gdrive_id=doc.gdrive_id,
    id=evidence_id,
    slug=slug,
  )


def set_evidence_slug(connection, evidence_id, slug):
  slug_sql = """
      UPDATE evidence SET slug=:slug WHERE id=:id
  """
  connection.execute(text(slug_sql),
                     slug=slug,
                     id=evidence_id)


def get_evidence_admin_acls(connection, evidence_id):
  sql = """
  SELECT 
    acl.ac_role_id,
    acl.context_id,
    acl.created_at,
    acl.updated_at,
    acl.object_id,
    acl.person_id,
    acl.modified_by_id,
    acl.id
  FROM access_control_list acl 
    WHERE acl.object_type='Evidence' AND acl.object_id=:evidence_id 
  """
  return connection.execute(text(sql), evidence_id=evidence_id)


def build_evidence_revision_content_acl(connection, evidence_id):
  result = []
  for acl_item in get_evidence_admin_acls(connection, evidence_id):
    modified_by = None
    if acl_item.modified_by_id:
      modified_by = {
        "person": {
          "href": "/api/people/{}".format(acl_item.modified_by_id),
          "type": "Person",
          "id": acl_item.modified_by_id
        }
      }

    result.append({
      "display_name": "",
      "ac_role_id": acl_item.ac_role_id,
      "context_id": acl_item.context_id,
      "created_at": acl_item.created_at.strftime('%Y-%m-%dT%H:%M:%S'),
      "object_type": "Evidence",
      "updated_at": acl_item.updated_at.strftime('%Y-%m-%dT%H:%M:%S'),
      "object_id": acl_item.object_id,
      "parent_id": None,
      "person": {
        "href": "/api/people/{}".format(acl_item.person_id),
        "type": "Person",
        "id": acl_item.person_id
      },
      "modified_by_id": acl_item.modified_by_id,
      "person_id": acl_item.person_id,
      "modified_by": modified_by,
      "type": "AccessControlList",
      "id": acl_item.id
    })
  return result


def build_evidence_revision_content(connection, evidence, migration_user_id):
  now = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
  content = {
    "status": "Active",
    "kind": evidence.kind,
    "send_by_default": True,
    "display_name": evidence.title,
    "description": evidence.description,
    "recipients": "Assignees,Creators,Verifiers",
    "title": evidence.title,
    "updated_at": now,
    "context_id": evidence.context_id,
    "created_at": now,
    "source_gdrive_id": evidence.source_gdrive_id,
    "slug": evidence.slug,
    "last_deprecated_date": None,
    "link": evidence.link,
    "modified_by_id": migration_user_id,
    "access_control_list": build_evidence_revision_content_acl(connection, evidence.id),
    "modified_by": {
      "person": {
        "href": "/api/people/{}".format(migration_user_id),
        "type": "Person",
        "id": migration_user_id
      }
    },
    "type": "Evidence",
    "id": evidence.id,
    "gdrive_id": evidence.gdrive_id
  }
  return content


def create_evidence_revision(connection, evidence, migration_user_id, event_id):
  sql = """
      INSERT INTO revisions (
        resource_id,
        resource_type,
        event_id,
        action,
        content,
        context_id,
        created_at,
        updated_at,
        modified_by_id,
        resource_slug)
      VALUES (:evid_id, "Evidence", :event_id, "created",
              :content, :context_id, NOW(), NOW(), :user_id, :resource_slug);
  """

  content = build_evidence_revision_content(connection, evidence, migration_user_id)
  connection.execute(
    text(sql),
    evid_id=evidence.id, event_id=event_id,
    content=json.dumps(content, ensure_ascii=False),
    context_id=evidence.context_id,
    user_id=migration_user_id, resource_slug=evidence.slug
  )


def create_relationship(connection, source_id, source_type, evid_id):
  """Create relationship for Evidence"""
  sql = """
      INSERT INTO relationships (
        source_id,
        source_type,
        destination_id,
        destination_type,
        created_at,
        updated_at,
        is_external)
      VALUES (:source_id, :source_type, :evid_id,
              'Evidence', NOW(), NOW(), '0');
  """
  connection.execute(text(sql),
                     source_id=source_id,
                     source_type=source_type,
                     evid_id=evid_id)
  inserted_id = last_insert_id(connection)
  return inserted_id


def create_rel_revision_content(rev_id, source_type,
                                source_id, destination_id):
  """Create content for new revision"""
  now = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

  content = {
    "parent_id": None,
    "context_id": None,
    "modified_by_id": None,
    "automapping_id": None,
    "modified_by": None,
    "type": "Relationship",
    'display_name': "{}:{} <-> Evidence:{}".format(source_type,
                                                   source_id,
                                                   destination_id),
    'created_at': now,
    'updated_at': now,
    'source_type': source_type,
    'source_id': source_id,
    'destination_type': 'Evidence',
    'destination_id': destination_id, 'id': rev_id
  }

  return content


# pylint: disable=too-many-arguments
def create_relationship_revision(connection, rel_id, source_id, source_type,
                                 destination_id, event_id, migration_user_id):
  """Create revision for relationship"""
  content = create_rel_revision_content(rel_id, source_type,
                                        source_id, destination_id)

  sql = """
      INSERT INTO revisions (
        resource_id,
        resource_type,
        event_id,
        action,
        content,
        created_at,
        updated_at,
        modified_by_id,
        source_type,
        source_id,
        destination_type,
        destination_id)
      VALUES (:rel_id, 'Relationship', :event_id,
              'created', :content, NOW(), NOW(),
              :modified_by_id, :source_type,
              :source_id, 'Evidence', :destination_id);
  """
  connection.execute(
    text(sql),
    rel_id=rel_id,
    event_id=event_id,
    content=json.dumps(content, ensure_ascii=False),
    modified_by_id=migration_user_id,
    source_type=source_type,
    source_id=source_id,
    destination_id=destination_id
  )


def copy_acl(connection, acl, evidence_id, acl_mapping):
  """Create copy of ACL object"""
  (_, person_id, ac_role_id, _, object_type,
   modified_by_id, context_id, parent_id) = acl
  sql = """
      INSERT INTO access_control_list (
        person_id,
        ac_role_id,
        object_id,
        object_type,
        modified_by_id,
        context_id,
        parent_id,
        created_at,
        updated_at)
      VALUES (:person_id, :ac_role_id, :evidence_id, :object_type,
              :modified_by_id, :context_id, :parent_id, NOW(), NOW())
  """
  connection.execute(text(sql),
                     person_id=acl.person_id,
                     ac_role_id=acl_mapping.get(acl.ac_role_id, acl.ac_role_id),
                     evidence_id=evidence_id,
                     object_type='Evidence',
                     modified_by_id=acl.modified_by_id,
                     context_id=acl.context_id,
                     parent_id=acl.parent_id)


def copy_acls(connection, doc_id, evidence_id, acl_mapping):
  results = connection.execute(text("""
      SELECT
        acl.id,
        acl.person_id,
        acl.ac_role_id,
        acl.object_id,
        acl.object_type,
        acl.modified_by_id,
        acl.context_id,
        acl.parent_id
      FROM access_control_list acl
      WHERE acl.object_type = 'Document'
      AND acl.object_id = :doc_id
  """), doc_id=doc_id).fetchall()

  for item in results:
    copy_acl(connection, item, evidence_id, acl_mapping)





def get_document_admin_role_id(connection):
  sql = """
    SELECT acr.id  FROM access_control_roles acr WHERE 
      acr.object_type='Document' AND name='Admin'
  """
  return connection.execute(text(sql)).fetchone()[0]


def build_acr_mapping(connection):
  sql = """
  SELECT acr1.id as acr_doc_id, acr2.id as acr_evid_id FROM access_control_roles acr1 
    JOIN access_control_roles acr2 ON acr1.name=acr2.name 
    WHERE acr1.object_type='Document' AND acr2.object_type='Evidence'
  UNION ALL
  SELECT acr1.id as acr_doc_id, acr2.id as acr_evid_id FROM access_control_roles acr1
    JOIN access_control_roles acr2 
      ON acr1.name='Auditors Document Mapped' AND acr2.name='Auditors Evidence Mapped'
  UNION ALL
  SELECT acr1.id as acr_doc_id, acr2.id as acr_evid_id FROM access_control_roles acr1 
    JOIN access_control_roles acr2 
      ON acr1.name='Verifiers Document Mapped' AND acr2.name='Verifiers Evidence Mapped'
  UNION ALL
  SELECT acr1.id as acr_doc_id, acr2.id as acr_evid_id FROM access_control_roles acr1 
    JOIN access_control_roles acr2 
      ON acr1.name='Creators Document Mapped' AND acr2.name='Creators Evidence Mapped'
  UNION ALL
  SELECT acr1.id as acr_doc_id, acr2.id as acr_evid_id FROM access_control_roles acr1
    JOIN access_control_roles acr2 
      ON acr1.name='Assignees Document Mapped' AND acr2.name='Assignees Evidence Mapped'
  """
  result = connection.execute(text(sql)).fetchall()
  return {k: v for k, v in result}


def delete_document_relationship(connection, rel_id):
  """Delete document relationship"""
  connection.execute(text('DELETE from relationships '
                          'where id = :rel_id'),
                     rel_id=rel_id)


def delete_migrated_document(connection, document_id):
  """Delete document"""
  connection.execute(text('DELETE from documents '
                          'where id = :document_id'),
                     document_id=document_id)


def process_doc(connection, doc, migration_user_id, event_id):
  acl_mapping = build_acr_mapping(connection)
  evidence = create_evidence(connection, doc)
  copy_acls(connection, doc.doc_id, evidence.id, acl_mapping)
  create_evidence_revision(connection, evidence, migration_user_id, event_id)
  relationship_id = create_relationship(connection, doc.counterparty_id,
                                        doc.counterparty_type, evidence.id)
  create_relationship_revision(connection, relationship_id, doc.counterparty_id,
                               doc.counterparty_type, evidence.id, event_id, migration_user_id)

  delete_migrated_document(connection, doc.doc_id)
  delete_document_relationship(connection, doc.rel_id)



def crete_event_for_revision(connection, user_id):
  """Create event for BULK document creation"""
  sql = """
      INSERT INTO events (
          modified_by_id,
          created_at,
          action,
          resource_type,
          updated_at)
      VALUES (:user_id, NOW(), 'BULK', 'Evidence', NOW());
  """
  connection.execute(text(sql), user_id=user_id)
  event_id = last_insert_id(connection)
  return event_id


def run_migration():
  connection = op.get_bind()
  migration_user_id = get_migration_user_id(connection)
  event_id = crete_event_for_revision(connection, migration_user_id)
  docs_to_migrate = get_docs_to_migrate(connection)
  for doc in docs_to_migrate:
    process_doc(connection, doc, migration_user_id, event_id)


def upgrade():
    """Upgrade database schema and/or data, creating a new revision."""
    run_migration()


def downgrade():
    """Downgrade database schema and/or data back to the previous revision."""

