# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""
Change relationship between assessment templates and audits not null

Create Date: 2018-05-08 14:52:25.534107
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name

from alembic import op

# revision identifiers, used by Alembic.
revision = '9bc9e8064e04'
down_revision = '4bce53d67bcf'


def remove_assessment_templates():
  """Remove assessment_templates with empty audit_id"""
  op.execute(
      "DELETE ast from assessment_templates ast"
      " WHERE ast.audit_id IS NULL"
  )


def alter_constraints():
  """Update fk_assessment_template_audits constraint"""
  op.execute("""
      ALTER TABLE assessment_templates
      DROP FOREIGN KEY fk_assessment_template_audits
  """)
  op.execute("""
      ALTER TABLE assessment_templates
      MODIFY audit_id int(11) NOT NULL
  """)

  op.execute("""
      ALTER TABLE assessment_templates
      ADD CONSTRAINT fk_assessment_template_audits
      FOREIGN KEY (audit_id) REFERENCES audits (id)
  """)


def upgrade():
  """Upgrade database schema and/or data, creating a new revision."""
  remove_assessment_templates()
  alter_constraints()


def downgrade():
  """Downgrade database schema and/or data back to the previous revision."""
  op.execute("""
      ALTER TABLE assessment_templates
      DROP FOREIGN KEY fk_assessment_template_audits
  """)
  op.execute("""
      ALTER TABLE assessment_templates
      MODIFY audit_id int(11) DEFAULT NULL
  """)
  op.execute("""
      ALTER TABLE assessment_templates
      ADD CONSTRAINT fk_assessment_template_audits
      FOREIGN KEY (audit_id) REFERENCES audits (id) ON DELETE SET NULL
  """)
