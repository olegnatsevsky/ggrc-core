# -*- coding: utf-8 -*-

# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Tests for notifications for models with Reviewable mixin."""
import datetime

import ddt

from integration.ggrc import TestCase
from integration.ggrc import generator

from ggrc.models import all_models
from ggrc.models import Notification

from integration.ggrc.models import factories


@ddt.ddt
class TestReviewNotification(TestCase):

  """Test notification on Review status change."""

  def setUp(self):
    super(TestReviewNotification, self).setUp()
    self.client.get("/login")
    self._fix_notification_init()
    self.generator = generator.ObjectGenerator()

  def _fix_notification_init(self):
    """Fix Notification object init function.

    This is a fix needed for correct created_at field when using freezgun. By
    default the created_at field is left empty and filed by database, which
    uses system time and not the fake date set by freezugun plugin. This fix
    makes sure that object created in feeze_time block has all dates set with
    the correct date and time.
    """

    def init_decorator(init):
      """Wrapper for Notification init function."""

      def new_init(self, *args, **kwargs):
        init(self, *args, **kwargs)
        if hasattr(self, "created_at"):
          self.created_at = datetime.datetime.now()
      return new_init

    Notification.__init__ = init_decorator(Notification.__init__)

  def test_old_comments(self):

    reviewer = factories.PersonFactory()

    reviewer_role_id = all_models.AccessControlRole.query.filter_by(
      name="Reviewer",
      object_type="Review",

    ).one().id

    with factories.single_commit():
      control = factories.ControlFactory()
      review = factories.ReviewFactory(
          reviewable=control,
          email_message="some comment"
      )
      factories.AccessControlListFactory(
          ac_role_id=reviewer_role_id, person=reviewer, object=review
      )
    self.generator.generate_relationship(
      source=control,
      destination=review,
    )

    # response = self.client.get("/_notifications/show_pending")

