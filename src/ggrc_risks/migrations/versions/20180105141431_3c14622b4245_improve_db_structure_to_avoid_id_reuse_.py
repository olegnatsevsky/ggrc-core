# Copyright (C) 2017 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
Improve db structure to avoid id reuse after db reboot

Create Date: 2018-01-05 14:14:31.925068
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name


# revision identifiers, used by Alembic.
from ggrc.migrations.utils import custom_autoincrement as cai

revision = '3c14622b4245'
down_revision = '3e667570f21f'


def upgrade():
  """Upgrade database schema and/or data, creating a new revision."""
  cai.migrate_and_create_triggers('ggrc_risks')


def downgrade():
  """Downgrade database schema and/or data back to the previous revision."""
  cai.downgrade_tables('ggrc_risks')
