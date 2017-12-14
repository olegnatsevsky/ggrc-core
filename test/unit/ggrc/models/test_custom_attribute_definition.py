# Copyright (C) 2017 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

""" Unit tests for the Custom attribute definition object """

import unittest

from ggrc.models import all_models
from ggrc.models import exceptions


class TestCAD(unittest.TestCase):
  """Test custom attribute definition"""

  def test_gca_person_type(self):
    """Remove possibility to add GCA with Person type for any object."""
    sut = all_models.CustomAttributeDefinition()
    with self.assertRaises(exceptions.ValidationError):
      sut.validate_attribute_type('', 'Map:Person')

  def test_lca_person_type(self):
    """LCA with Person type should work as before."""
    sut = all_models.CustomAttributeDefinition()
    sut.definition_id = 1
    result = sut.validate_attribute_type('', 'Map:Person')
    self.assertEquals(result, 'Map:Person')
