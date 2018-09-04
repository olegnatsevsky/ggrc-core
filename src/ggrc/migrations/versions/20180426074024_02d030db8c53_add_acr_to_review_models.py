# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
add ACR to review models

Create Date: 2018-04-26 07:40:24.548244
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name


from alembic import op


# revision identifiers, used by Alembic.
revision = '02d030db8c53'
down_revision = '2c659b2fdac1'


def upgrade():
  """Upgrade database schema and/or data, creating a new revision."""
  op.execute("""
       INSERT INTO access_control_roles
          (name, object_type, `read`, `update`, `delete`,
           mandatory, non_editable, internal, created_at, updated_at)
       VALUES ('Reviewer', 'Review', 1, 1, 0, 1, 1, 0, NOW(), NOW())
  """)


def downgrade():
  """Downgrade database schema and/or data back to the previous revision."""
  op.execute("""
      DELETE FROM access_control_roles
        WHERE name="Reviewer" AND object_type="Review"
      """)
