# Copyright (C) 2017 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name

"""
Add custom autoincrement based on trigger, function and sequence table.
"""
from alembic import op


tables = {
    'ggrc': [
        'access_control_list',
        'access_control_roles',
        'access_groups',
        'assessments',
        'assessment_templates',
        'audits',
        'audit_objects',
        'automappings',
        'background_tasks',
        'categorizations',
        'clauses',
        'comments',
        'contexts',
        'controls',
        'custom_attribute_values',
        'data_assets',
        'documents',
        'facilities',
        'helps',
        'issues',
        'markets',
        'notifications',
        'notification_types',
        'notification_configs',
        'objectives',
        'object_people',
        'org_groups',
        'people',
        'directives',
        'products',
        'programs',
        'projects',
        'relationships',
        'sections',
        'snapshots',
        'systems',
        'vendors',
        'issuetracker_issues',
        'labels',
        'object_labels'
    ],
    'ggrc_basic_permissions': [
        'context_implications',
        'user_roles',
    ],
    'ggrc_risks': [
        'risks',
        'risk_objects',
        'threats',
    ],
    'ggrc_risk_assessments': [
        'risk_assessments',
    ],
    'ggrc_workflows': [
        'cycle_task_entries',
        'cycle_task_group_object_tasks',
        'cycle_task_groups',
        'cycles',
        'task_group_objects',
        'task_group_tasks',
        'task_groups',
        'workflow_people',
        'workflows',

        # table 'roles' moved here from 'ggrc_basic_permissions' because of
        # migration 55501ef0f634, as it adds workflow role. We need to migrate
        # data and set trigger afterwards.

        'roles',
        'custom_attribute_definitions',
    ],
}


def migrate_and_create_trigger_for_table(table_name, id_field='id'):
  """Migrate data and create triggers from given table."""
  op.execute("""
        INSERT INTO sequences
          SELECT '{table_name}', IFNULL(MAX({id_field}), 0) FROM {table_name}
  """.format(table_name=table_name, id_field=id_field))

  op.execute("""
        CREATE TRIGGER trig_{table_name}
          BEFORE INSERT ON {table_name}
          FOR EACH ROW SET new.{id_field}=get_next_id('{table_name}')
  """.format(table_name=table_name, id_field=id_field))


def migrate_and_create_triggers(module_name):
  """Migrate data and create triggers from given module."""
  for table_name in tables[module_name]:
    migrate_and_create_trigger_for_table(table_name)


def downgrade_tables(module_name):
  """Downgrade tables from given module."""
  for table_name in tables[module_name]:
    op.execute('DROP TRIGGER trig_{}'.format(table_name))
