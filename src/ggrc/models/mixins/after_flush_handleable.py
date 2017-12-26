# Copyright (C) 2017 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Module contains AfterFlushHandleable mixin."""

from sqlalchemy import event
from sqlalchemy.orm import session


class AfterFlushHandleable(object):
  """A mixin for handling after_flash sqlalchemy events.

  Used if you need to handle object in a after flush state.
  e.g if needed to validate object when all fields are filled.
  """

  # pylint: disable=too-few-public-methods
  def handle_after_flush(self):
    """Override with custom handling"""
    raise NotImplementedError()

  @classmethod
  def _loop_handler(cls, alchemy_session, flush_context):
    """loop thought all object in session and call handler"""
    # pylint: disable=unused-argument

    for obj in alchemy_session:
      if isinstance(obj, AfterFlushHandleable):
        obj.handle_after_flush()

# pylint: disable=protected-access
event.listen(session.Session, 'after_flush',
             AfterFlushHandleable._loop_handler)
