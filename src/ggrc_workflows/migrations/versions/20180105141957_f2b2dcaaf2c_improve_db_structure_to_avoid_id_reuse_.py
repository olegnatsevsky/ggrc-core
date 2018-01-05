# Copyright (C) 2017 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
Improve db structure to avoid id reuse after db reboot

Create Date: 2018-01-05 14:19:57.987713
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name

from ggrc.migrations.utils import custom_autoincrement as cai


# revision identifiers, used by Alembic.
revision = 'f2b2dcaaf2c'
down_revision = '14b87f599ede'


def upgrade():
  """Upgrade database schema and/or data, creating a new revision."""
  cai.migrate_and_create_triggers('ggrc_workflows')


def downgrade():
  """Downgrade database schema and/or data back to the previous revision."""
  cai.downgrade_tables('ggrc_workflows')
