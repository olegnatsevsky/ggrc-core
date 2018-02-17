# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Factories that create entities."""
# pylint: disable=too-many-arguments
# pylint: disable=invalid-name
# pylint: disable=redefined-builtin

import copy
import random

from lib import factory
from lib.constants import (element, objects, roles, value_aliases,
                           url as const_url, messages)
from lib.constants.element import (
    CustomAttributesTypes, GlobalCustomAttributesTypes)
from lib.entities.entity import (
    PersonEntity, CustomAttributeDefinitionEntity, CommentEntity)
from lib.utils import help_utils, string_utils
from lib.utils.string_utils import StringMethods


class EntitiesFactory(object):
  """Common factory class for entities."""
  # pylint: disable=too-few-public-methods

  def __init__(self, obj_name):
    self.obj_name = obj_name
    self.obj_type = objects.get_obj_type(self.obj_name)
    self.obj_title = self.generate_string(self.obj_type)
    self.obj_entity_cls = factory.get_cls_obj_entity(object_name=self.obj_name)
    if self.__class__ not in [CustomAttributeDefinitionEntity, PersonEntity,
                              CommentEntity]:
      self.obj_slug = self.generate_slug()

  def obj_inst(self):
    """Create object's instance and set value for attribute type."""
    return self.obj_entity_cls().update_attrs(
        is_allow_none=False, type=self.obj_type)

  def _create_random_obj(self, is_add_rest_attrs):
    """Create object's instance with random and predictable attributes' values.
    (method for overriding).
    """
    raise NotImplementedError

  def create(self, is_add_rest_attrs=False, **attrs):
    """Create random object's instance, if 'is_add_rest_attrs' then add
    attributes for REST, if 'attrs' then update attributes accordingly.
    """
    return self._create_random_obj(
        is_add_rest_attrs=is_add_rest_attrs).update_attrs(
        is_allow_none=False, **attrs)

  @classmethod
  def generate_string(cls, first_part):
    """Generate string in unicode format according object type and random data.
    """
    return unicode("{first_part}_{uuid}_{rand_str}".format(
        first_part=first_part, uuid=StringMethods.random_uuid(),
        rand_str=StringMethods.random_string()))

  @classmethod
  def generate_slug(cls):
    """Generate slug in unicode format according str part and random data."""
    return unicode("{slug}".format(slug=StringMethods.random_uuid()))

  @classmethod
  def generate_email(cls, domain=const_url.DEFAULT_EMAIL_DOMAIN):
    """Generate email in unicode format according to domain."""
    return unicode("{mail_name}@{domain}".format(
        mail_name=StringMethods.random_uuid(), domain=domain))


class PeopleFactory(EntitiesFactory):
  """Factory class for Persons entities."""

  def __init__(self):
    super(PeopleFactory, self).__init__(objects.PEOPLE)

  @staticmethod
  def extract_people_emails(people):
    """Extract values for person's email attributes."""
    return [
        person.email for person in help_utils.convert_to_list(people)
        if isinstance(person, PersonEntity)]

  @property
  def default_user(self):
    """Create object's instance for default system superuser."""
    return PersonEntity().update_attrs(
        type=self.obj_type,
        name=roles.DEFAULT_USER, id=1, href=const_url.DEFAULT_USER_HREF,
        email=const_url.DEFAULT_USER_EMAIL, system_wide_role=roles.SUPERUSER)

  @staticmethod
  def get_acl_members(role_id, people):
    """Return ACL the same members as list of dicts:
    [{ac_role_id: *, person: {id: *}, ...]
    """
    def get_acl_member(role_id, person):
      """Return ACL member as dict: {ac_role_id: *, person: {id: *}."""
      if isinstance(person, PersonEntity):
        return {"ac_role_id": role_id, "person": person.repr_min_dict()}
      else:
        raise ValueError(messages.CommonMessages.err_common.format(
            PersonEntity, person))
    return [get_acl_member(role_id, person)
            for person in help_utils.convert_to_list(people)]

  def _create_random_obj(self, is_add_rest_attrs):
    """Create Person entity with randomly and predictably filled fields, if
    'is_add_rest_attrs' then add attributes for REST."""
    person_obj = self.obj_inst().update_attrs(
        name=self.obj_title, email=self.generate_email(),
        system_wide_role=unicode(random.choice(roles.GLOBAL_ROLES)))
    return person_obj


class CommentsFactory(EntitiesFactory):
  """Factory class for Comments entities."""

  def __init__(self):
    super(CommentsFactory, self).__init__(objects.COMMENTS)

  def _create_random_obj(self, is_add_rest_attrs):
    """Create Comment entity with randomly and predictably filled fields, if
    'is_add_rest_attrs' then add attributes for REST."""
    comment_obj = self.obj_inst().update_attrs(
        description=self.obj_title,
        modified_by=PeopleFactory().default_user.name)
    if is_add_rest_attrs:
      comment_obj.update_attrs(
          assignee_type=",".join((
              unicode(roles.PRIMARY_CONTACTS),
              unicode(roles.SECONDARY_CONTACTS))))
    return comment_obj


class CustomAttributeDefinitionsFactory(EntitiesFactory):
  """Factory class for entities."""

  def __init__(self):
    super(CustomAttributeDefinitionsFactory, self).__init__(
        objects.CUSTOM_ATTRIBUTES)

  @classmethod
  def generate_ca_values(cls, list_ca_def_objs, is_none_values=False):
    """Generate dictionary of CA random values from exist list CA definitions
    objects according to CA 'id', 'attribute_type' and 'multi_choice_options'
    for Dropdown. Return dictionary of CA items that ready to use via REST API:
    If 'is_none_values' then generate None like CA values according to CA
    definitions types.
    Example:
    list_ca_objs = [{'attribute_type': 'Text', 'id': 1},
    {'attribute_type': 'Dropdown', 'id': 2, 'multi_choice_options': 'a,b,c'}]
    :return {"1": "text_example", "2": "b"}
    """
    def generate_ca_value(cls, ca):
      """Generate CA value according to CA 'id', 'attribute_type' and
      'multi_choice_options' for Dropdown.
      """
      if not isinstance(ca, dict):
        ca = ca.__dict__
      ca_attr_type = ca.get("attribute_type")
      ca_value = None
      if ca_attr_type in CustomAttributesTypes.CAS_TYPES:
        if not is_none_values:
          if ca_attr_type in (CustomAttributesTypes.TEXT,
                              CustomAttributesTypes.RICH_TEXT):
            ca_value = cls.generate_string(ca_attr_type)
          if ca_attr_type == CustomAttributesTypes.DATE:
            ca_value = unicode(ca["created_at"][:10])
          if ca_attr_type == CustomAttributesTypes.CHECKBOX:
            ca_value = random.choice((True, False))
          if ca_attr_type == CustomAttributesTypes.DROPDOWN:
            ca_value = unicode(
                random.choice(ca["multi_choice_options"].split(",")))
          if ca_attr_type == CustomAttributesTypes.PERSON:
            ca_value = ":".join([unicode(ca["modified_by"]["type"]),
                                 unicode(ca["modified_by"]["id"])])
        else:
          ca_value = (
              None if ca_attr_type != CustomAttributesTypes.CHECKBOX
              else u"0")
      return {ca["id"]: ca_value}
    return {
        k: v for _ in [generate_ca_value(cls, ca) for ca in list_ca_def_objs]
        for k, v in _.items()}

  @staticmethod
  def generate_ca_defenitions_for_asmt_tmpls(list_ca_definitions):
    """Generate list of dictionaries of CA random values from exist list CA
    definitions according to CA 'title', 'attribute_type' and
    'multi_choice_options' for Dropdown. Return list of dictionaries of CA
    definitions that ready to use via REST API:
    Example:
    :return
    [{"title": "t1", "attribute_type": "Text", "multi_choice_options": ""},
     {"title":"t2", "attribute_type":"Rich Text", "multi_choice_options":""}]
    """
    return [{k: (v if v else "") for k, v in ca_def.__dict__.items()
             if k in ("title", "attribute_type", "multi_choice_options")}
            for ca_def in list_ca_definitions]

  def create_dashboard_ca(self, definition_type):
    """Create and return CA entity with valid filled fields for creating
    N'Dashboard'.
    """
    return self.obj_inst().update_attrs(
        title=self.generate_string(value_aliases.DASHBOARD),
        attribute_type=GlobalCustomAttributesTypes.TEXT,
        definition_type=definition_type, mandatory=False)

  def create(self, is_add_rest_attrs=False, **attrs):
    """Create random Custom Attribute object's instance, if
    'is_add_rest_attrs' then add attributes for REST, if 'attrs' then update
    attributes accordingly.
    """
    ca_obj = self._create_random_obj(is_add_rest_attrs=is_add_rest_attrs)
    return self._update_ca_attrs_values(obj=ca_obj, **attrs)

  def _create_random_obj(self, is_add_rest_attrs):
    """Create Custom Attribute entity with randomly and predictably filled
    fields, if 'is_add_rest_attrs' then add attributes for REST."""
    ca_obj_attr_type = unicode(random.choice(
        CustomAttributesTypes.CAS_TYPES))
    ca_obj = self.obj_inst().update_attrs(
        title=self.generate_string(ca_obj_attr_type),
        attribute_type=ca_obj_attr_type,
        multi_choice_options=(
            StringMethods.random_list_strings()
            if ca_obj_attr_type == CustomAttributesTypes.DROPDOWN
            else None),
        definition_type=unicode(objects.get_singular(
            random.choice(objects.ALL_CA_OBJS))), mandatory=False)
    if is_add_rest_attrs:
      ca_obj.update_attrs(
          modal_title="Add Attribute to type {}".format(
              ca_obj.definition_type.title()))
    return ca_obj

  def _update_ca_attrs_values(self, obj, **attrs):
    """Update CA's (obj) attributes values according to dictionary of
    arguments (key = value). Restrictions: 'multi_choice_options' is a
    mandatory attribute for Dropdown CA and 'placeholder' is a attribute that
    exists only for Text and Rich Text CA.
    Generated data - 'obj', entered data - '**arguments'.
    """
    # fix generated data
    if attrs.get("attribute_type"):
      obj.title = self.generate_string(attrs["attribute_type"])
    if (obj.multi_choice_options and
            obj.attribute_type == CustomAttributesTypes.DROPDOWN and
            attrs.get("attribute_type") !=
            CustomAttributesTypes.DROPDOWN):
      obj.multi_choice_options = None
    # fix entered data
    if (attrs.get("multi_choice_options") and
            attrs.get("attribute_type") !=
            CustomAttributesTypes.DROPDOWN):
      attrs["multi_choice_options"] = None
    if (attrs.get("placeholder") and attrs.get("attribute_type") not in
        (CustomAttributesTypes.TEXT,
         CustomAttributesTypes.RICH_TEXT)):
      attrs["placeholder"] = None
    # extend entered data
    if (attrs.get("attribute_type") ==
            CustomAttributesTypes.DROPDOWN and not
            obj.multi_choice_options):
      obj.multi_choice_options = StringMethods.random_list_strings()
    return obj.update_attrs(**attrs)


class ProgramsFactory(EntitiesFactory):
  """Factory class for Programs entities."""
  def_user = PeopleFactory().default_user

  def __init__(self, obj_creator=def_user):
    super(ProgramsFactory, self).__init__(objects.PROGRAMS)
    self.managers = [obj_creator]

  def _create_random_obj(self, is_add_rest_attrs):
    """Create Program entity with randomly and predictably filled fields, if
    'is_add_rest_attrs' then add attributes for REST."""
    program_obj = self.obj_inst().update_attrs(
        title=self.obj_title, slug=self.obj_slug,
        status=unicode(element.ObjectStates.DRAFT),
        managers=PeopleFactory.extract_people_emails(self.managers),
        os_state=unicode(element.ReviewStates.UNREVIEWED))
    if is_add_rest_attrs:
      program_obj.update_attrs(
          recipients=",".join((
              unicode(roles.ADMIN), unicode(roles.PRIMARY_CONTACTS),
              unicode(roles.SECONDARY_CONTACTS))),
          access_control_list=string_utils.StringMethods.
          convert_list_elements_to_list(
              [PeopleFactory.get_acl_members(
                  roles.ACLRolesIDs.PROGRAM_MANAGERS, self.managers)]))
    return program_obj


class ControlsFactory(EntitiesFactory):
  """Factory class for Controls entities."""
  def_user = PeopleFactory().default_user

  def __init__(self, obj_creator=def_user):
    super(ControlsFactory, self).__init__(objects.CONTROLS)
    self.admins = [obj_creator]

  def _create_random_obj(self, is_add_rest_attrs):
    """Create Control entity with randomly and predictably filled fields, if
    'is_add_rest_attrs' then add attributes for REST."""
    control_obj = self.obj_inst().update_attrs(
        title=self.obj_title, slug=self.obj_slug,
        status=unicode(element.ObjectStates.DRAFT),
        admins=PeopleFactory.extract_people_emails(self.admins),
        os_state=unicode(element.ReviewStates.UNREVIEWED))
    if is_add_rest_attrs:
      control_obj.update_attrs(
          recipients=",".join((
              unicode(roles.ADMIN), unicode(roles.PRIMARY_CONTACTS),
              unicode(roles.SECONDARY_CONTACTS))),
          access_control_list=string_utils.StringMethods.
          convert_list_elements_to_list(
              [PeopleFactory.get_acl_members(
                  roles.ACLRolesIDs.CONTROL_ADMINS, self.admins)]))
    return control_obj


class ObjectivesFactory(EntitiesFactory):
  """Factory class for Objectives entities."""
  def_user = PeopleFactory().default_user

  def __init__(self, obj_creator=def_user):
    super(ObjectivesFactory, self).__init__(objects.OBJECTIVES)
    self.admins = [obj_creator]

  def _create_random_obj(self, is_add_rest_attrs):
    """Create Objective entity with randomly and predictably filled fields, if
    'is_add_rest_attrs' then add attributes for REST."""
    objective_obj = self.obj_inst().update_attrs(
        title=self.obj_title, slug=self.obj_slug,
        status=unicode(element.ObjectStates.DRAFT),
        admins=PeopleFactory.extract_people_emails(self.admins),
        os_state=unicode(element.ReviewStates.UNREVIEWED))
    if is_add_rest_attrs:
      objective_obj.update_attrs(
          recipients=",".join((
              unicode(roles.ADMIN), unicode(roles.PRIMARY_CONTACTS),
              unicode(roles.SECONDARY_CONTACTS))),
          access_control_list=string_utils.StringMethods.
          convert_list_elements_to_list(
              [PeopleFactory.get_acl_members(
                  roles.ACLRolesIDs.OBJECTIVE_ADMINS, self.admins)]))
    return objective_obj


class AuditsFactory(EntitiesFactory):
  """Factory class for Audit entity."""
  def_user = PeopleFactory().default_user

  def __init__(self, obj_creator=def_user):
    super(AuditsFactory, self).__init__(objects.AUDITS)
    self.admins = [obj_creator]

  @staticmethod
  def clone(audit, count_to_clone=1):
    """Clone Audit entity (count depends on 'count_to_clone')
    and set attributes' values related to parallelization to None, title will
    be predicted.
    """
    # pylint: disable=anomalous-backslash-in-string
    return [copy.deepcopy(audit).update_attrs(
        title=unicode(audit.title + " - copy " + str(num)), slug=None,
        created_at=None, updated_at=None, href=None, url=None, id=None)
        for num in xrange(1, count_to_clone + 1)]

  def _create_random_obj(self, is_add_rest_attrs):
    """Create Audit entity with randomly and predictably filled fields, if
    'is_add_rest_attrs' then add attributes for REST."""
    audit_obj = self.obj_inst().update_attrs(
        title=self.obj_title, slug=self.obj_slug,
        audit_captains=PeopleFactory.extract_people_emails(self.admins),
        os_state=unicode(element.AuditStates.PLANNED))
    if is_add_rest_attrs:
      audit_obj.update_attrs(
          access_control_list=string_utils.StringMethods.
          convert_list_elements_to_list(
              [PeopleFactory.get_acl_members(
                  roles.ACLRolesIDs.AUDIT_CAPTAINS, self.admins)]))
    return audit_obj


class AssessmentTemplatesFactory(EntitiesFactory):
  """Factory class for Assessment Templates entities."""

  def __init__(self):
    super(AssessmentTemplatesFactory, self).__init__(
        objects.ASSESSMENT_TEMPLATES)

  @staticmethod
  def clone(asmt_tmpl, count_to_clone=1):
    """Clone Assessment Template entity (count depends on 'count_to_clone')
    and set attributes' values related to parallelization to None.
    """
    return [copy.deepcopy(asmt_tmpl).update_attrs(
        slug=None, updated_at=None, href=None, url=None, id=None)
        for _ in xrange(1, count_to_clone + 1)]

  def _create_random_obj(self, is_add_rest_attrs):
    """Create Assessment Template entity with randomly and predictably filled
    fields, if 'is_add_rest_attrs' then add attributes for REST."""
    asmt_tmpl_obj = self.obj_inst().update_attrs(
        title=self.obj_title, slug=self.obj_slug,
        assignees=unicode(roles.PRINCIPAL_ASSIGNEES),
        verifiers=unicode(roles.AUDITORS),
        status=unicode(element.ObjectStates.DRAFT),
        template_object_type=objects.get_obj_type(objects.CONTROLS))
    if is_add_rest_attrs:
      elements = element.CommonAudit
      asmt_tmpl_obj.update_attrs(
          default_people={
              "assignees": asmt_tmpl_obj.assignees,
              "verifiers": asmt_tmpl_obj.verifiers},
          people_values=[{"value": v, "title": t} for v, t in [
              (roles.ADMIN, elements.OBJECT_ADMINS),
              (roles.AUDIT_LEAD, elements.AUDIT_CAPTAIN),
              (roles.AUDITORS, elements.AUDITORS),
              (roles.PRINCIPAL_ASSIGNEES, elements.PRINCIPAL_ASSIGNEES),
              (roles.SECONDARY_ASSIGNEES, elements.SECONDARY_ASSIGNEES),
              (roles.PRIMARY_CONTACTS, elements.PRIMARY_CONTACTS),
              (roles.SECONDARY_CONTACTS, elements.SECONDARY_CONTACTS),
              (roles.OTHER, elements.OTHERS)]])
    return asmt_tmpl_obj


class AssessmentsFactory(EntitiesFactory):
  """Factory class for Assessments entities."""
  def_user = PeopleFactory().default_user

  def __init__(self, obj_creator=def_user):
    super(AssessmentsFactory, self).__init__(objects.ASSESSMENTS)
    self.admins = [obj_creator]
    self.assignees = [self.def_user]

  def obj_inst(self):
    """Create Assessment object's instance and set values for attributes:
    type, verified, status.
    """
    return self.obj_entity_cls().update_attrs(
        is_allow_none=False, type=self.obj_type, verified=False,
        status=unicode(element.AssessmentStates.NOT_STARTED))

  def generate(self, mapped_objects, audit, asmt_tmpl=None):
    """Generate Assessment objects' instances under 'audit' based on info
    about 'mapped_objects' and 'asmt_tmpl' use generation logic accordingly.
    """
    mapped_objects = help_utils.convert_to_list(mapped_objects)
    asmts_creators = PeopleFactory.extract_people_emails(self.admins)
    asmts_assignees = audit.audit_captains
    asmts_verifiers = (
        audit.auditors if audit.auditors else audit.audit_captains)
    asmts_cas_def = None
    asmts_type = (
        mapped_objects[0].type
        if all(getattr(mapped_obj, "type") for mapped_obj in mapped_objects)
        else None)
    if asmt_tmpl:
      if asmts_type != asmt_tmpl.template_object_type:
        raise ValueError(
            "Mapped objects' type: {} have to be the same with Assessment "
            "Template's type: {}".format(
                asmts_type, asmt_tmpl.template_object_type))
      # if assignees or verifiers are ids (int not str related attrs)
      # todo add logic to converts ids (int) repr to users' names
      if any(all(isinstance(user, int) for user in asmts_users)
             for asmts_users in
             [asmts_users for asmts_users in asmts_assignees, asmts_verifiers
              if isinstance(asmts_users, list)]):
        raise NotImplementedError
      if asmt_tmpl.assignees == unicode(roles.AUDITORS):
        asmts_assignees = audit.auditors
      if asmt_tmpl.verifiers != unicode(roles.AUDITORS):
        asmts_verifiers = audit.audit_captains

      if getattr(asmt_tmpl, "custom_attribute_definitions"):
        asmts_cas_def = asmt_tmpl.custom_attribute_definitions
    asmts_objs = [
        empty_asmt.update_attrs(
            title=mapped_object.title + " assessment for " + audit.title,
            audit=audit.title, mapped_objects=[mapped_object],
            creators=asmts_creators, assignees=asmts_assignees,
            verifiers=asmts_verifiers, assessment_type=asmts_type,
            custom_attribute_definitions=asmts_cas_def
        ) for empty_asmt, mapped_object
        in zip([self.obj_inst() for _ in xrange(len(mapped_objects))],
               mapped_objects)]
    return asmts_objs

  def create(self, is_add_rest_attrs=False, **attrs):
    """Create random Assessment object's instance, if 'is_add_rest_attrs' then
    add attributes for REST, if 'attrs' then update attributes accordingly.
    """
    asmt_obj = self._create_random_obj(
        is_add_rest_attrs=is_add_rest_attrs).update_attrs(
        is_allow_none=False, **attrs)
    # todo: add global logic to update attrs 'ACLs to People', 'People to ACLs'
    if getattr(asmt_obj, "verifiers"):
      asmt_obj.update_attrs(
          verifiers=PeopleFactory.extract_people_emails(attrs["verifiers"]),
          access_control_list=string_utils.StringMethods.
          convert_list_elements_to_list(
              asmt_obj.access_control_list + [PeopleFactory.get_acl_members(
                  roles.ACLRolesIDs.ASSESSMENT_VERIFIERS,
                  attrs["verifiers"])]))
    return asmt_obj

  def _create_random_obj(self, is_add_rest_attrs):
    """Create Assessment entity with randomly and predictably filled fields, if
    'is_add_rest_attrs' then add attributes for REST."""
    asmt_obj = self.obj_inst().update_attrs(
        title=self.obj_title, slug=self.obj_slug,
        status=unicode(element.AssessmentStates.NOT_STARTED),
        creators=PeopleFactory.extract_people_emails(self.admins),
        assignees=PeopleFactory.extract_people_emails(self.assignees),
        assessment_type=objects.get_obj_type(objects.CONTROLS), verified=False)
    if is_add_rest_attrs:
      asmt_obj.update_attrs(
          recipients=",".join((
              unicode(roles.ASSIGNEES), unicode(roles.CREATORS),
              unicode(roles.VERIFIERS))),
          access_control_list=string_utils.StringMethods.
          convert_list_elements_to_list(
              [PeopleFactory.get_acl_members(
                  roles.ACLRolesIDs.ASSESSMENT_CREATORS, self.admins),
               PeopleFactory.get_acl_members(
                   roles.ACLRolesIDs.ASSESSMENT_ASSIGNEES, self.assignees)]))
    return asmt_obj


class IssuesFactory(EntitiesFactory):
  """Factory class for Issues entities."""
  def_user = PeopleFactory().default_user

  def __init__(self, obj_creator=def_user):
    super(IssuesFactory, self).__init__(objects.ISSUES)
    self.admins = [obj_creator]

  def _create_random_obj(self, is_add_rest_attrs):
    """Create Issue entity with randomly and predictably filled fields, if
    'is_add_rest_attrs' then add attributes for REST."""
    issue_obj = self.obj_inst().update_attrs(
        title=self.obj_title, slug=self.obj_slug,
        status=unicode(element.IssueStates.DRAFT),
        admins=PeopleFactory.extract_people_emails(self.admins),
        os_state=unicode(element.ReviewStates.UNREVIEWED))
    if is_add_rest_attrs:
      issue_obj.update_attrs(
          recipients=",".join((
              unicode(roles.ADMIN), unicode(roles.PRIMARY_CONTACTS),
              unicode(roles.SECONDARY_CONTACTS))),
          access_control_list=string_utils.StringMethods.
          convert_list_elements_to_list(
              [PeopleFactory.get_acl_members(
                  roles.ACLRolesIDs.ISSUE_ADMINS, self.admins)]))
    return issue_obj
