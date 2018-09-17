# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
Fix reviewer acr to make mandatory

Create Date: 2018-09-17 14:26:41.623257
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name

from alembic import op


# revision identifiers, used by Alembic.
revision = '0c2741cea492'
down_revision = 'c465979824fc'


def upgrade():
    """Upgrade database schema and/or data, creating a new revision."""
    op.execute("""
        UPDATE access_control_roles SET mandatory=1 WHERE name = 'Reviewer'
        AND object_type='Review'
  """)


def downgrade():
    """Downgrade database schema and/or data back to the previous revision."""
