# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
add reviews table

Create Date: 2018-04-12 07:24:21.832352
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name

import sqlalchemy as sa

from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '2c659b2fdac1'
down_revision = 'ba1e6a203f07'


def upgrade():
    """Upgrade database schema and/or data, creating a new revision."""
    op.create_table(
        'reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('reviewable_id', sa.Integer(), nullable=False),
        sa.Column('reviewable_type', sa.String(length=250), nullable=False),
        sa.Column('notification_type',
                  sa.Enum('email', 'issue_tracker'),
                  nullable=False),
        sa.Column('email_message', sa.Text(), nullable=False),
        # sa.Column('agenda', sa.Text(), nullable=False),
        sa.Column('last_reviewed_by_id', sa.Integer(), nullable=True),
        sa.Column('last_reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=250), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('modified_by_id', sa.Integer(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('context_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['context_id'], ['contexts.id'], ),
        sa.ForeignKeyConstraint(['last_reviewed_by_id'], ['people.id'], ),
        sa.ForeignKeyConstraint(['created_by_id'], ['people.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('fk_reviews_contexts', 'reviews', ['context_id'], unique=False)
    op.create_index('ix_reviews_updated_at', 'reviews', ['updated_at'], unique=False)


def downgrade():
    """Downgrade database schema and/or data back to the previous revision."""
    op.drop_index('ix_reviews_updated_at', table_name='reviews')
    op.drop_index('fk_reviews_contexts', table_name='reviews')
    op.drop_table('reviews')
