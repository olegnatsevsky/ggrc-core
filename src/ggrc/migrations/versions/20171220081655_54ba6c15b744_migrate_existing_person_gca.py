# Copyright (C) 2017 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
Migrate existing person global custom attributes into custom roles.

Create Date: 2017-12-20 08:16:55.978986
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name

from alembic import op


# revision identifiers, used by Alembic.
revision = '54ba6c15b744'
down_revision = '4f01efeeba4d'


def upgrade():
  """Upgrade database schema and/or data, creating a new revision."""
  op.execute("""
      CREATE TEMPORARY TABLE gca_migration_mapping (
        definition_type VARCHAR(250),
        object_type VARCHAR(250)
      );
  """)

  op.execute("""
      INSERT INTO gca_migration_mapping VALUES
        ('access_group','AccessGroup'),
        ('assessment',	'Assessment'),
        ('clause','Clause'),
        ('contract','Contract'),
        ('control',	'Control'),
        ('data_asset','DataAsset'),
        ('facility','Facility'),
        ('issue','Issue'),
        ('market','Market'),
        ('objective','Objective'),
        ('org_group','OrgGroup'),
        ('policy','Policy'),
        ('product','Product'),
        ('program','Program'),
        ('project','Project'),
        ('regulation','Regulation'),
        ('risk','Risk'),
        ('section','Section'),
        ('standard','Standard'),
        ('system','System'),
        ('threat','Threat'),
        ('vendor','Vendor');
  """)
  op.execute("""
      INSERT INTO access_control_roles (
        access_control_roles.name,
        access_control_roles.object_type,
        access_control_roles.tooltip,
        access_control_roles.modified_by_id,
        access_control_roles.created_at,
        access_control_roles.updated_at,
        access_control_roles.read,
        access_control_roles.update,
        access_control_roles.delete,
        access_control_roles.mandatory,
        access_control_roles.default_to_current_user,
        access_control_roles.non_editable,
        access_control_roles.internal
      )
      SELECT
        cad.title,
        gmm.object_type,
        cad.helptext,
        cad.modified_by_id,
        cad.created_at,
        NOW(),
        0,
        0,
        0,
        cad.mandatory,
        0,
        0,
        0
      FROM custom_attribute_definitions cad
      JOIN gca_migration_mapping gmm ON
        cad.definition_type = gmm.definition_type
      WHERE cad.attribute_type = 'Map:person' AND
        definition_id IS null;
  """)
  op.execute("SET SESSION SQL_SAFE_UPDATES = 0;")
  op.execute("""
      DELETE cad FROM custom_attribute_definitions cad
      JOIN gca_migration_mapping gmm ON
        cad.definition_type = gmm.definition_type
      WHERE cad.attribute_type = 'Map:person' AND
        cad.definition_id IS NULL;
  """)


def downgrade():
  """Downgrade database schema and/or data back to the previous revision."""
