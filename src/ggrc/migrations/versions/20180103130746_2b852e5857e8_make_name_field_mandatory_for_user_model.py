# Copyright (C) 2017 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
Make name field mandatory for User model

Create Date: 2018-01-03 13:07:46.321664
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision = '2b852e5857e8'
down_revision = '3911f39325b4'


def upgrade():
  """Upgrade database schema and/or data, creating a new revision."""
  op.execute("""
      UPDATE people 
      SET name = SUBSTRING_INDEX(email, '@', 1)
      WHERE name is NULL;    
  """)

  op.execute("""
      ALTER TABLE people
      MODIFY name VARCHAR(250) NOT NULL;
  """)


def downgrade():
  """Downgrade database schema and/or data back to the previous revision."""
  op.execute("""
      ALTER TABLE people
      MODIFY name VARCHAR(250) NULL;
  """)
