# Copyright (C) 2017 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Tests for custom autoincrement."""
from ggrc import db
from integration.ggrc import TestCase
from integration.ggrc.models import factories


class TestCustomAutoincrement(TestCase):
  """Tests for custom autoincrement."""
  # pylint: disable=invalid-name

  @staticmethod
  def _update_custom_autoincr_value(new_value):
    db.session.execute("""
      INSERT INTO sequences VALUES ('controls', {})
    """.format(new_value))

  @staticmethod
  def _update_native_autoincr_value(new_value):
    db.session.execute("ALTER TABLE controls AUTO_INCREMENT = {}"
                       .format(new_value))

  def test_custom_autoincrement(self):
    """Check autoincrement is taken from sequence table."""
    id_value = 7
    self._update_custom_autoincr_value(id_value)
    control = factories.ControlFactory()
    self.assertEqual(control.id, 8)

  def test_custom_autoincrement_reboot_emulation(self):
    """Check that custom autoincrement value is resistant to
    table's autoincrement change"""

    with factories.single_commit():
      factories.ControlFactory()
      control2 = factories.ControlFactory()

    db.session.delete(control2)
    db.session.commit()
    self._update_native_autoincr_value(1)
    control3 = factories.ControlFactory()
    self.assertEqual(control3.id, 3)
