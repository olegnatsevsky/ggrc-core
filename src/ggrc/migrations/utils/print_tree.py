# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""This is a helper function for inspecting the access control table.

This function prints the access control table in form of a human readable
propagation tree.

Example:

  Audit
      Audit Captains RUD
          Relationship R
              AssessmentTemplate RUD
              Issue RUD
                  Relationship R
                      Comment R
                      Document CU
              Assessment RUD
                  Relationship R
                      Comment R
                      Document CU
              Document CU
          Snapshot CU
  ...

"""

import collections

# pylint: disable=unused-import
# This is needed so that this script can be run as an independent python
# script, since we have issues with importing models without importing the
# entire app first.
import sys

from ggrc import app  # noqa
from ggrc import models


def get_acr_id_map(acrs):
  return {acr.id: acr for acr in acrs}


def get_acr_parent_id_map(acrs):
  """Get mappings from parent id to all children."""
  parent_map = collections.defaultdict(set)
  for acr in acrs:
    if acr.parent_id:
      parent_map[acr.parent_id].add(acr)
  return parent_map


def get_acr_dict(acrs):
  """Get all acrs based on object type and name."""
  acr_dict = collections.defaultdict(dict)
  for acr in acrs:
    if not acr.parent_id and not acr.internal:
      acr_dict[acr.object_type][acr.name] = acr
  return acr_dict


def get_rud(acr):
  """Get RUD representation of read update delete flags."""
  rud = (["", "R"][acr.read], ["", "U"][acr.update], ["", "D"][acr.delete])
  return "".join(rud)


PRINT_CHILDREN_MAPPING = {
    True: '{}"{} {}": {{',
    False: "{}{} {}"
}

PRINT_CHILDREN_END_MAPPING = {
    True: "{}  }},",
    False: ""
}

OBJECT_TYPE_PRINT_MAPPING = {
    True: '"{}": {{',
    False: "{}"
}

ACR_NAME_PRINT_MAPPING = {
    True: '    "{}": {{ #{}',
    False: "    {} {}"
}

ACR_NAME_END_MAPPING = {
    True: "    },",
    False: ""
}

PRINT_TREE_END_PRINT_MAPPING = {
    True: "},",
    False: ""
}

PRINT_TREE_END = {
    True: "}",
    False: ""
}

PRINT_TREE_NAME = {
    True: "TREE = {",
    False: ""
}


def print_not_empty(str_to_print):
  if str_to_print:
    print(str_to_print)


def print_children(acr, id_map, parent_map, as_dict, prefix="        "):
  """Print acr children and their sub-trees."""
  for child in parent_map[acr.id]:
    print_not_empty(PRINT_CHILDREN_MAPPING[as_dict].format(
        prefix, child.object_type, get_rud(child)
    ))
    print_children(child, id_map, parent_map, as_dict, prefix=prefix + "    ")
    print_not_empty(PRINT_CHILDREN_END_MAPPING[as_dict].format(prefix))


def print_tree(as_dict):
  """Print the full acr propagation tree."""
  acrs = models.AccessControlRole.query.order_by(
      models.AccessControlRole.parent_id,
      models.AccessControlRole.object_type,
  )
  acr_dict = get_acr_dict(acrs)
  id_map = get_acr_id_map(acrs)
  parent_map = get_acr_parent_id_map(acrs)
  for object_type, acrs in acr_dict.items():
    print_not_empty(OBJECT_TYPE_PRINT_MAPPING[as_dict].format(object_type))
    for acr_name in sorted(acrs):
      print_not_empty(ACR_NAME_PRINT_MAPPING[as_dict].format(
          acr_name,
          get_rud(acrs[acr_name])
      ))
      print_children(acrs[acr_name], id_map, parent_map, as_dict)
      print_not_empty(ACR_NAME_END_MAPPING[as_dict])
    print_not_empty(PRINT_TREE_END_PRINT_MAPPING[as_dict])


if __name__ == "__main__":
  as_dict = False
  if len(sys.argv) == 2 and sys.argv[1] == "--as_dict":
    as_dict = True
  print_not_empty(PRINT_TREE_NAME[as_dict])
  print_tree(as_dict)
  print_not_empty(PRINT_TREE_END[as_dict])
