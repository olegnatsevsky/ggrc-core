# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
Add Review ACL

Create Date: 2018-08-27 13:48:47.637936
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name
import copy

# revision identifiers, used by Alembic.
import itertools

from ggrc.migrations.utils.acr_propagation import update_acr_propagation_tree
from ggrc.migrations.utils.acr_propagation_object_review import CURRENT_TREE

revision = 'c465979824fc'
down_revision = '02d030db8c53'


def _update_sub_tree(branch, flag="RUD"):
  branch["Requirement {}".format(flag)]["Relationship R"]["Review RU"] = {}
  branch["Vendor {}".format(flag)]["Relationship R"]["Review RU"] = {}
  branch["Market {}".format(flag)]["Relationship R"]["Review RU"] = {}
  branch["AccessGroup {}".format(flag)]["Relationship R"]["Review RU"] = {}
  branch["Metric {}".format(flag)]["Relationship R"]["Review RU"] = {}
  branch["Objective {}".format(flag)]["Relationship R"]["Review RU"] = {}
  branch["Clause {}".format(flag)]["Relationship R"]["Review RU"] = {}
  branch["OrgGroup {}".format(flag)]["Relationship R"]["Review RU"] = {}
  branch["System {}".format(flag)]["Relationship R"]["Review RU"] = {}
  branch["Policy {}".format(flag)]["Relationship R"]["Review RU"] = {}
  branch["Threat {}".format(flag)]["Relationship R"]["Review RU"] = {}
  branch["Contract {}".format(flag)]["Relationship R"]["Review RU"] = {}
  branch["Process {}".format(flag)]["Relationship R"]["Review RU"] = {}
  branch["Control {}".format(flag)]["Relationship R"]["Review RU"] = {}
  branch["Product {}".format(flag)]["Relationship R"]["Review RU"] = {}
  branch["Risk {}".format(flag)]["Relationship R"]["Review RU"] = {}
  branch["DataAsset {}".format(flag)]["Relationship R"]["Review RU"] = {}
  branch["ProductGroup {}".format(flag)]["Relationship R"]["Review RU"] = {}
  branch["Standard {}".format(flag)]["Relationship R"]["Review RU"] = {}
  branch["Project {}".format(flag)]["Relationship R"]["Review RU"] = {}
  branch["Facility {}".format(flag)]["Relationship R"]["Review RU"] = {}
  branch["Regulation {}".format(flag)]["Relationship R"]["Review RU"] = {}
  branch["TechnologyEnvironment {}".format(flag)]["Relationship R"]["Review RU"] = {}


def _update_program(new_tree):
  new_tree["Program"]["Primary Contacts"]["Relationship R"]["Review RU"] = {}
  new_tree["Program"]["Secondary Contacts"]["Relationship R"]["Review RU"] = {}

  pr_editor_related = new_tree["Program"]["Program Editors"]["Relationship R"]
  pr_editor_related["Review RU"] = {}
  _update_sub_tree(pr_editor_related)

  pr_manager_related = new_tree["Program"]["Program Managers"]["Relationship R"]
  pr_manager_related["Review RU"] = {}
  _update_sub_tree(pr_manager_related)

  pr_reader_related = new_tree["Program"]["Program Readers"]["Relationship R"]
  pr_reader_related["Review R"] = {}
  _update_sub_tree(pr_reader_related, flag="R")


def _update_object(branch):
  branch["Admin"]["Relationship R"]["Review RU"] = {}
  branch["Legal Counsels"]["Relationship R"]["Review RU"] = {}
  branch["Primary Contacts"]["Relationship R"]["Review RU"] = {}
  branch["Product Managers"]["Relationship R"]["Review RU"] = {}
  branch["Secondary Contacts"]["Relationship R"]["Review RU"] = {}
  branch["System Owners"]["Relationship R"]["Review RU"] = {}
  branch["Technical / Program Managers"]["Relationship R"]["Review RU"] = {}
  branch["Technical Leads"]["Relationship R"]["Review RU"] = {}


def _update_simple_object(branch):
  branch["Admin"]["Relationship R"]["Review RU"] = {}
  branch["Primary Contacts"]["Relationship R"]["Review RU"] = {}
  branch["Secondary Contacts"]["Relationship R"]["Review RU"] = {}


def _update_control(branch):
  _update_simple_object(branch)
  branch["Principal Assignees"]["Relationship R"]["Review RU"] = {}
  branch["Secondary Assignees"]["Relationship R"]["Review RU"] = {}


OBJECTS = {
  "TechnologyEnvironment",
  "OrgGroup",
  "AccessGroup",
  "System",
  "ProductGroup",
  "Product",
  "Vendor",
  "Project",
  "DataAsset",
  "Facility",
  "Process",
}

SIMPLE_OBJECTS = {
  "Objective",
  "Regulation",
  "Policy",
  "Risk",
  "Standard",
  "Contract",
  "Requirement",
  "Clause",
  "Metric",
  "Market",
  "Threat",
}


def build_review_subtree():
  res = {}
  for obj in itertools.chain(OBJECTS, SIMPLE_OBJECTS, {"Control", "Program"}):
    res["{} R".format(obj)] = {
      "Relationship R": {
        "Document R": {
          "Relationship R": {
            "Comment R": {},
          },
        },
        "Comment R": {},
      },
    }
  return res


def add_review_subtree(new_tree):
  new_tree["Review"]["Reviewer"] = {
    "Relationship R": build_review_subtree()
  }


def update_tree():
  new_tree = copy.deepcopy(CURRENT_TREE)
  _update_program(new_tree)
  _update_control(new_tree["Control"])
  for obj in OBJECTS:
    _update_object(new_tree[obj])
  for simple_obj in SIMPLE_OBJECTS:
    _update_simple_object(new_tree[simple_obj])
  add_review_subtree(new_tree)
  return new_tree


def upgrade():
  """Upgrade database schema and/or data, creating a new revision."""
  new_tree = update_tree()
  update_acr_propagation_tree(CURRENT_TREE, new_tree)


def downgrade():
  """Downgrade database schema and/or data back to the previous revision."""
