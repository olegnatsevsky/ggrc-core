# Copyright (C) 2017 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
Improve db structure to avoid id reuse after db reboot

Create Date: 2018-01-04 11:21:06.696106
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name


from alembic import op


# revision identifiers, used by Alembic.
from ggrc.migrations.utils import custom_autoincrement as cai
revision = '1800660a24a6'
down_revision = '3911f39325b4'

special_id_tables = [
    ('attribute_types', 'attribute_type_id'),
    ('attribute_definitions', 'attribute_definition_id'),
    ('attribute_templates', 'attribute_template_id'),
    ('namespaces', 'namespace_id'),
    ('object_templates', 'object_template_id'),
    ('object_types', 'object_type_id')
]


def upgrade():
  """Upgrade database schema and/or data, creating a new revision."""

  op.execute("""
      CREATE TABLE sequences (
        table_name CHAR(50) PRIMARY KEY,
        id_value INT(11)
      )
  """)

  op.execute("""
      CREATE FUNCTION get_next_id (table_name CHAR(50))
      RETURNS INT(11)
      BEGIN
        INSERT INTO sequences VALUES (table_name,LAST_INSERT_ID(1))
        ON DUPLICATE KEY UPDATE id_value=LAST_INSERT_ID(id_value+1);
        RETURN LAST_INSERT_ID();
      END
  """)

  cai.migrate_and_create_triggers('ggrc')

  for table_name, id_field in special_id_tables:
    cai.migrate_and_create_trigger_for_table(table_name, id_field)


def downgrade():
  """Downgrade database schema and/or data back to the previous revision."""
  op.execute("DROP TABLE sequences")
  op.execute("DROP FUNCTION get_next_id")
  cai.downgrade_tables('ggrc')
  for table_name, _ in special_id_tables:
    op.execute('DROP TRIGGER trig_{}'.format(table_name))
