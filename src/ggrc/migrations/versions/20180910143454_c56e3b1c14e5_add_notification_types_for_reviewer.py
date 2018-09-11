# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
Add notification types for reviewer

Create Date: 2018-09-10 14:34:54.392756
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision = 'c56e3b1c14e5'
down_revision = 'c465979824fc'


def upgrade():
  """Upgrade database schema and/or data, creating a new revision."""
  op.execute("""
    INSERT INTO notification_types (
      name, description, advance_notice,
      template, instant, created_at, updated_at
    ) 
    VALUES (
      'review_request_created',
      'Notify reviewers review is requested.',
      '0', 
      'review_request_created',
      '0', NOW(), NOW()),
      (
      'review_status_unreviewed',
      'Notify reviewers, admins, primary contacts, secondary contacts review is unreviewed.',
      '0', 
      'review_status_unreviewed',
      '0', NOW(), NOW())
  """)
  op.execute("""
    ALTER TABLE notifications 
      ADD runner ENUM('daily', 'fast') NOT NULL DEFAULT 'daily'
  """)
  op.execute("""
      ALTER TABLE notifications_history 
        ADD runner ENUM('daily', 'fast') NOT NULL DEFAULT 'daily'
  """)

  op.execute("""
    ALTER TABLE access_control_roles 
      ADD notify_about_review_status tinyint(1) NOT NULL DEFAULT '0'
  """)





def downgrade():
  """Downgrade database schema and/or data back to the previous revision."""

