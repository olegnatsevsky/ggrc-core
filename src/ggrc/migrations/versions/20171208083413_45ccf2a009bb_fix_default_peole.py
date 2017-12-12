# Copyright (C) 2017 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
Fix default_peole for old Assessment templates

Create Date: 2017-12-08 08:34:13.915060
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name

from alembic import op

# revision identifiers, used by Alembic.
revision = '45ccf2a009bb'
down_revision = '1af0b27960a2'


def upgrade():
  """Upgrade database schema and/or data, creating a new revision."""
  op.execute("""
      UPDATE assessment_templates
      SET default_people = REPLACE(
          default_people, '"assessors":', '"assignees":'
      )
      WHERE default_people like '%"assessors":%'
  """)


def downgrade():
  """Downgrade database schema and/or data back to the previous revision."""
  op.execute("""
      UPDATE assessment_templates
      SET default_people = REPLACE(
          default_people, '"assignees":', '"assessors":'
      )
      WHERE default_people like '%"assignees":%'
  """)
