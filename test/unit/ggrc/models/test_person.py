"""Test person model"""

import unittest
from ggrc.models import Person


class TestPerson(unittest.TestCase):
  """Tests for Person model"""

  def test_name_not_null_constraint(self):
    """Test of not null constraint"""
    p = Person()
    p.email = 'some@email.com'
