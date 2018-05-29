# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""
Remove unmapped documents

Create Date: 2018-05-29 14:15:37.583927
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name

from alembic import op
from sqlalchemy import text
from ggrc.migrations.utils import crete_event
from ggrc.migrations.utils import migrator

revision = '8ffc6d30dba2'
down_revision = '2efe5292b7ac'


def create_temporary_table():
  """Tmp table to store document.id"""
  op.execute("SET AUTOCOMMIT = 1")
  sql = """
      CREATE TEMPORARY TABLE documents_to_deprecate (
        id int(11) NOT NULL
      )
  """
  op.execute(sql)


def save_documents_no_relationships():
  """Get  document.id and store to temp_table documents_to_deprecate"""
  sql = """
      INSERT INTO documents_to_deprecate (id)
        SELECT d.id FROM documents d
          LEFT OUTER JOIN (
            SELECT DISTINCT (ur.doc_id) FROM(
              SELECT r.source_id AS doc_id FROM relationships r
                  WHERE r.source_type = 'Document'
              UNION ALL
              SELECT r.destination_id AS doc_id FROM relationships r
                  WHERE r.destination_type = 'Document'
            ) AS ur
          ) AS result ON d.id = result.doc_id
        WHERE result.doc_id IS NULL AND d.updated_at < "2018-06-12"
  """
  op.execute(sql)


def remove_documents(connection, migrator_id):
  """Remove documents"""
  sql = """
      DELETE FROM documents
      WHERE id in (SELECT dtd.id FROM documents_to_deprecate dtd)
  """
  connection.execute(text(sql), migrator_id=migrator_id)


def get_latest_revision(connection, doc_id):
  """Get slug and content of the latest revision for given document"""
  sql = """
      SELECT r.resource_slug, r.content FROM revisions r WHERE
      r.resource_id=:doc_id AND
      r.resource_type="Document" order by r.created_at DESC LIMIT 1
  """
  return connection.execute(text(sql), doc_id=doc_id).fetchone()


def get_document_ids(connection):
  return connection.execute("SELECT id FROM documents_to_deprecate")


# pylint: disable=too-many-arguments
def create_deleted_revision(connection, slug, doc_id, content,
                            event_id, migrator_id):
  """Create 'deleted' revision"""
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
        resource_slug
      )
      VALUES (
        :resource_id,
        "Document",
        :event_id,
        "deleted",
        :content,
        NOW(),
        NOW(),
        :modified_by_id,
        :resource_slug
      )
  """
  connection.execute(
      text(sql),
      resource_id=doc_id,
      event_id=event_id,
      content=content,
      modified_by_id=migrator_id,
      resource_slug=slug
  )


def create_deprecated_revisions(connection, event_id, migrator_id):
  """Add documents that is not in objects_without_revisions to create rev"""
  for doc_id_pr in get_document_ids(connection):
    doc_id = doc_id_pr.id
    latest_revision = get_latest_revision(connection, doc_id)
    if latest_revision:
      create_deleted_revision(connection, latest_revision.resource_slug,
                              doc_id, latest_revision.content,
                              event_id, migrator_id)


def upgrade():
  """Upgrade database schema and/or data, creating a new revision."""
  connection = op.get_bind()
  migrator_id = migrator.get_migration_user_id(connection)
  event_id = crete_event(connection, migrator_id, resource_type="Document")

  create_temporary_table()
  save_documents_no_relationships()
  create_deprecated_revisions(connection, event_id, migrator_id)
  remove_documents(connection, migrator_id)
  remove_tmp_table()


def remove_tmp_table():
  """Remove temporary table"""
  op.execute("DROP TABLE IF EXISTS documents_to_deprecate")
  op.execute("SET AUTOCOMMIT = 0;")


def downgrade():
  """Downgrade database schema and/or data back to the previous revision."""
