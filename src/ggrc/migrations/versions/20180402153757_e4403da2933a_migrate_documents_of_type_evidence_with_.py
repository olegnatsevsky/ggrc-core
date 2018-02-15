# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
Migrate documents of type Evidence with invalid gdrive URLs to document.URL

Create Date: 2018-04-02 15:37:57.922876
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name

from sqlalchemy.sql import text
from alembic import op


# revision identifiers, used by Alembic.
revision = 'e4403da2933a'
down_revision = '48a49f384b2e'


def get_audit_docs_ids(connection):
  sql = """
  SELECT distinct d.id 
    FROM
      documents as d
    JOIN relationships as r
      ON r.destination_id = d.id
    WHERE
      r.destination_type = 'Document' AND 
      d.document_type in ('EVIDENCE', 'REFERENCE_URL') AND
      r.source_type ='Audit'
    UNION ALL
    SELECT
        d.id
    FROM
      documents as d
    JOIN relationships as r
      ON r.source_id = d.id
    WHERE
      r.source_type = 'Document' AND 
      d.document_type in ('EVIDENCE', 'REFERENCE_URL') AND
      r.destination_type ='Audit'
  """
  res = connection.execute(text(sql)).fetchall()
  return [i.id for i in res]


def migrate_docs(connection):
  audit_doc_ids = get_audit_docs_ids(connection)
  assessment_doc_ids = get_assessment_docs_ids(connection)
  invalid_gdrive_url_doc_ids = get_invalid_gdrive_url_doc_ids(connection)
  doc_ids = audit_doc_ids + assessment_doc_ids + invalid_gdrive_url_doc_ids

  if doc_ids:
    sql = """
      UPDATE documents SET document_type = 'URL'
      WHERE id IN :doc_ids
    """
    connection.execute(text(sql), doc_ids=doc_ids)


def get_assessment_docs_ids(connection):
  sql = """
    SELECT  distinct d.id 
      FROM
        documents as d
      JOIN relationships as r
        ON r.destination_id = d.id
      WHERE
        r.destination_type = 'Document' AND 
        d.document_type  = 'REFERENCE_URL' AND
        r.source_type ='Assessment'
      UNION ALL
      SELECT
          d.id
      FROM
        documents as d
      JOIN relationships as r
        ON r.source_id = d.id
      WHERE
        r.source_type = 'Document' AND 
        d.document_type = 'REFERENCE_URL' AND
        r.destination_type ='Assessment'
  """
  res = connection.execute(text(sql)).fetchall()
  return [i.id for i in res]


def get_invalid_gdrive_url_doc_ids(connection):
  sql = """
  SELECT
    d.id 
  FROM
    documents as d
  JOIN relationships as r
    ON r.destination_id = d.id
  JOIN assessments a 
    ON a.id=r.source_id
  WHERE
    r.destination_type = 'Document' AND
    d.document_type  = 'EVIDENCE' and LOCATE('?id=',d.link)=0 and LOCATE('/d/',d.link)=0
    and r.source_type ='Assessment'
  UNION ALL
  SELECT
      d.id
  FROM
    documents as d
  JOIN relationships as r
    ON r.source_id = d.id
  JOIN assessments a 
    ON a.id=r.destination_id
  WHERE
    r.source_type = 'Document' AND
    d.document_type = 'EVIDENCE' and LOCATE('?id=',d.link)=0 and LOCATE('/d/',d.link)=0
    and r.destination_type ='Assessment'
  """
  res = connection.execute(text(sql)).fetchall()
  return [i.id for i in res]


def rename_doc_fields():
  op.execute("""
      ALTER TABLE documents CHANGE document_type kind enum('URL','FILE','REFERENCE_URL', 'EVIDENCE') NOT NULL DEFAULT 'URL';
  """)
  op.execute('SET SESSION SQL_SAFE_UPDATES = 0;')
  op.execute("UPDATE documents SET kind = 'FILE' where kind = 'EVIDENCE';")

  op.execute("""
      ALTER TABLE documents MODIFY kind enum('URL','FILE','REFERENCE_URL') NOT NULL DEFAULT 'URL';
  """)


def run_migration(connection):
  migrate_docs(connection)
  rename_doc_fields()


def upgrade():
  """Upgrade database schema and/or data, creating a new revision."""
  connection = op.get_bind()
  run_migration(connection)


def downgrade():
  """Downgrade database schema and/or data back to the previous revision."""
#   TODO: add schema downgrade
