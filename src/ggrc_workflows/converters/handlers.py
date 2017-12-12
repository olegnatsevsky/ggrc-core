# Copyright (C) 2017 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>


""" Module for all special column handlers for workflow objects """

from sqlalchemy import inspection
from sqlalchemy import or_

from ggrc import db
from ggrc.converters import errors
from ggrc.converters.handlers import boolean
from ggrc.converters.handlers import handlers
from ggrc.converters.handlers import multi_object
from ggrc.login import get_current_user
from ggrc.utils import user_generator
from ggrc_basic_permissions import models as bp_models
from ggrc_workflows import models as wf_models


class WorkflowColumnHandler(handlers.ParentColumnHandler):

  """ handler for workflow column in task groups """

  def __init__(self, row_converter, key, **options):
    """ init workflow handler """
    self.parent = wf_models.Workflow
    super(WorkflowColumnHandler, self).__init__(row_converter, key, **options)


class TaskGroupColumnHandler(handlers.ParentColumnHandler):

  """ handler for task group column in task group tasks """

  def __init__(self, row_converter, key, **options):
    """ init task group handler """
    self.parent = wf_models.TaskGroup
    super(TaskGroupColumnHandler, self).__init__(row_converter, key, **options)


class CycleTaskGroupColumnHandler(handlers.ParentColumnHandler):

  """ handler for task group column in task group tasks """

  def __init__(self, row_converter, key, **options):
    """ init task group handler """
    self.parent = wf_models.CycleTaskGroup
    super(CycleTaskGroupColumnHandler, self) \
        .__init__(row_converter, key, **options)


class UnitColumnHandler(handlers.ColumnHandler):

  """Handler for workflow 'repeat every' units column."""

  def parse_item(self):
    """Parse Unit column value."""
    value = self.raw_value.lower().strip()
    if value in {"-", "--", "---"}:
      self.set_empty = True
      value = None
    elif not value:
      value = None

    if not self.row_converter.is_new and self.raw_value:
      insp = inspection.inspect(self.row_converter.obj)
      unit_prev = getattr(insp.attrs, self.key).history.unchanged
      if value not in unit_prev:
        self.add_warning(errors.UNMODIFIABLE_COLUMN,
                         column_name=self.display_name)
        self.set_empty = False
      return None

    if value and value not in wf_models.Workflow.VALID_UNITS:
      self.add_error(errors.WRONG_VALUE_ERROR,
                     column_name=self.display_name)
      return None

    return value


class RepeatEveryColumnHandler(handlers.ColumnHandler):

  """Handler for workflow 'repeat every' column."""

  def parse_item(self):
    """Parse 'repeat every' value
    """
    value = self.raw_value.strip()
    if value in {"-", "--", "---"}:
      self.set_empty = True
      value = None
    elif value:
      try:
        value = int(self.raw_value)
        if not (0 < value < 31):
          raise ValueError
      except ValueError:
        self.add_error(errors.WRONG_VALUE_ERROR,
                       column_name=self.display_name)
        return
    else:
      # if it is an empty string
      value = None

    # check if value is unmodified for existing workflow
    if not self.row_converter.is_new and self.raw_value:
      insp = inspection.inspect(self.row_converter.obj)
      repeat_prev = getattr(insp.attrs, self.key).history.unchanged
      if value not in repeat_prev:
        self.add_warning(errors.UNMODIFIABLE_COLUMN,
                         column_name=self.display_name)
        self.set_empty = False
      return None

    return value

  def get_value(self):
    """Get 'Repeat Every' user readable value for Workflow."""
    value = super(RepeatEveryColumnHandler, self).get_value()
    if value:
      return str(value)
    return ""


class TaskTypeColumnHandler(handlers.ColumnHandler):

  """Handler for task type column in task group tasks."""

  type_map = {
      "rich text": "text",
      "dropdown": "menu",
      "drop down": "menu",
      "checkboxes": "checkbox",
      "checkbox": "checkbox",
  }

  reverse_map = {
      "text": "rich text",
      "menu": "dropdown",
      "checkbox": "checkbox"
  }

  def parse_item(self):
    """Parse task type column value."""
    value = self.type_map.get(self.raw_value.lower())
    if value is None:
      if self.raw_value.lower() in self.type_map.values():
        value = self.raw_value.lower()
    if value is None:
      value = self.row_converter.obj.default_task_type()
      default_value = self.reverse_map.get(value).title()
      if self.raw_value:
        self.add_warning(errors.WRONG_REQUIRED_VALUE,
                         value=self.raw_value,
                         column_name=self.display_name)
      else:
        self.add_warning(errors.MISSING_VALUE_WARNING,
                         default_value=default_value,
                         column_name=self.display_name)
    return value

  def get_value(self):
    """Get titled user readable value for taks type."""
    return self.reverse_map.get(self.row_converter.obj.task_type,
                                "rich text").title()


class WorkflowPersonColumnHandler(handlers.UserColumnHandler):
  """Common handler for Workflow people import/export."""

  def parse_item(self):
    users = self.get_users_list()
    if self.row_converter.is_new and self.mandatory and not users:
      self.add_error(errors.MISSING_VALUE_ERROR, column_name=self.display_name)
    return users

  def set_obj_attr(self):
    if not self.row_converter.obj.context:
      personal_context = get_current_user().get_or_create_object_context(
          context=1)
      workflow_context = self.row_converter.obj.get_or_create_object_context(
          personal_context)
      self.row_converter.obj.context = workflow_context

  def _add_workflow_people(self, role_name):
    """Add people to Workflow with appropriate role.

    Args:
        role_name: Workflow user role name
    """
    role = db.session.query(bp_models.Role).filter(
        bp_models.Role.name == role_name).first()
    for person in self.value:
      wf_models.WorkflowPerson(
          workflow=self.row_converter.obj,
          person=person,
          context=self.row_converter.obj.context,
          modified_by=get_current_user(),
      )
      bp_models.UserRole(
          person=person,
          role=role,
          context=self.row_converter.obj.context,
          modified_by=get_current_user(),
      )

  def _get_user_ids_query_for(self, role_name):
    """Prepare query to get people ids for everybody with specific role.

    Args:
        role_name: Workflow user role name

    Returns:
        Query for getting people ids who has role_name in scope of workflow
    """
    role_query = db.session.query(bp_models.Role.id).filter(
        bp_models.Role.name == role_name
    )
    return db.session.query(bp_models.UserRole.person_id).filter(
        bp_models.UserRole.context_id == self.row_converter.obj.context_id,
        bp_models.UserRole.role_id.in_(role_query.subquery())
    )

  def _get_people_emails_for(self, role_name):
    """Get people emails for everybody with specific role.

    Args:
        role_name: Workflow user role name

    Returns:
        Tuple of users' emails who has role_name in scope of workflow
    """
    user_ids_query = self._get_user_ids_query_for(role_name)
    emails = db.session.query(bp_models.Person.email).filter(
        bp_models.Person.id.in_(user_ids_query.subquery())
    )
    return (email for email, in emails)

  def _remove_people_with_role(self, role_name):
    """Remove people with specific role.

    Args:
        role_name: Workflow user role name
    """
    user_ids_query = self._get_user_ids_query_for(role_name)
    new_people_ids = [p.id for p in self.value]
    workflow_people_query = db.session.query(wf_models.WorkflowPerson).filter(
        wf_models.WorkflowPerson.workflow_id == self.row_converter.obj.id,
        or_(wf_models.WorkflowPerson.person_id.in_(user_ids_query.subquery()),
            wf_models.WorkflowPerson.person_id.in_(new_people_ids))
    )
    workflow_people_query.delete(synchronize_session='fetch')
    # We are getting user_ids from user_roles table.
    # Next line deletes user_role records related to specific users.
    user_ids_query.delete(synchronize_session='fetch')


class WorkflowOwnerColumnHandler(WorkflowPersonColumnHandler):
  """Column handler for WorklfowManagers import/export."""

  def get_value(self):
    return '\n'.join(self._get_people_emails_for('WorkflowOwner'))

  def set_obj_attr(self):
    if self.dry_run or not self.value:
      return
    super(WorkflowOwnerColumnHandler, self).set_obj_attr()
    self._remove_people_with_role('WorkflowOwner')
    new_people_ids = [p.id for p in self.value]
    # Remove collisions with WorkflowMember roles
    user_role_query = self._get_user_ids_query_for('WorkflowMember')
    user_role_query = user_role_query.filter(
        bp_models.UserRole.person_id.in_(new_people_ids))
    user_role_query.delete(synchronize_session='fetch')
    self._add_workflow_people('WorkflowOwner')


class WorkflowMemberColumnHandler(WorkflowPersonColumnHandler):
  """Column handler for WorklfowMembers import/export."""

  def parse_item(self):
    users = super(WorkflowMemberColumnHandler, self).parse_item()
    if ('workflow_owner' in self.row_converter.attrs and
            self.row_converter.attrs['workflow_owner'].value):
      owners = self.row_converter.attrs['workflow_owner'].value
    else:
      owners = user_generator.find_users(
          self._get_people_emails_for('WorkflowOwner'))
    return list(set(users) - set(owners))

  def get_value(self):
    return '\n'.join(self._get_people_emails_for('WorkflowMember'))

  def set_obj_attr(self):
    if self.dry_run or not self.value:
      return
    super(WorkflowMemberColumnHandler, self).set_obj_attr()
    self._remove_people_with_role('WorkflowMember')
    self._add_workflow_people('WorkflowMember')


class ObjectsColumnHandler(multi_object.ObjectsColumnHandler):

  def get_value(self):
    task_group_objects = wf_models.TaskGroupObject.query.filter_by(
        task_group_id=self.row_converter.obj.id).all()
    lines = ["{}: {}".format(t.object._inflector.title_singular.title(),
                             t.object.slug)
             for t in task_group_objects if t.object is not None]
    return "\n".join(lines)

  def insert_object(self):
    obj = self.row_converter.obj
    existing = set((t.object_type, t.object_id)
                   for t in obj.task_group_objects)
    for object_ in self.value:
      if (object_.type, object_.id) in existing:
        continue
      tgo = wf_models.TaskGroupObject(
          task_group=obj,
          object=object_,
          context=obj.context,
      )
      db.session.add(tgo)
    db.session.flush()


class CycleWorkflowColumnHandler(handlers.ExportOnlyColumnHandler):

  def get_value(self):
    return self.row_converter.obj.workflow.slug


class CycleColumnHandler(handlers.ExportOnlyColumnHandler):

  def get_value(self):
    return self.row_converter.obj.cycle.slug


class TaskDescriptionColumnHandler(handlers.TextareaColumnHandler):

  def set_obj_attr(self):
    """ Set task attribute based on task type """
    if not self.value or self.row_converter.ignore:
      return
    if self.row_converter.obj.task_type == "text":
      self.row_converter.obj.description = self.value
    else:
      options = [v.strip() for v in self.value.split(",")]
      self.row_converter.obj.response_options = options

  def get_value(self):
    if self.row_converter.obj.task_type == "text":
      return self.row_converter.obj.description
    else:
      return ", ".join(self.row_converter.obj.response_options)


COLUMN_HANDLERS = {
    "default": {
        "cycle": CycleColumnHandler,
        "cycle_task_group": CycleTaskGroupColumnHandler,
        "cycle_workflow": CycleWorkflowColumnHandler,
        "unit": UnitColumnHandler,
        "repeat_every": RepeatEveryColumnHandler,
        "notify_on_change": boolean.CheckboxColumnHandler,
        "task_description": TaskDescriptionColumnHandler,
        "task_group": TaskGroupColumnHandler,
        "task_group_objects": ObjectsColumnHandler,
        "task_type": TaskTypeColumnHandler,
        "workflow": WorkflowColumnHandler,
        "finished_date": handlers.NullableDateColumnHandler,
        "verified_date": handlers.NullableDateColumnHandler,
        "workflow_owner": WorkflowOwnerColumnHandler,
        "workflow_member": WorkflowMemberColumnHandler,
    },
}
