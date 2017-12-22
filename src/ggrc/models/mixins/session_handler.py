import collections
from sqlalchemy import event
from sqlalchemy.orm import session

BEFORE_FLUSH = 'before_flush'
AFTER_FLUSH = 'after_flush'

REGISTRY = collections.defaultdict(lambda: collections.defaultdict(list))


def register(event_type, obj, handler):
  REGISTRY[event_type][obj].append(handler)


def _generic_handler(alchemy_session, event_type):
  for obj in alchemy_session:
    for registered_class in REGISTRY[event_type]:
      if isinstance(obj, registered_class):
        for handler in REGISTRY[event_type][registered_class]:
          handler(obj)


def after_flush_handlers(alchemy_session, flush_context):
  _ = flush_context
  _generic_handler(alchemy_session, AFTER_FLUSH)


def before_flush_handlers(alchemy_session, flush_context, instances):
  _ = flush_context, instances
  _generic_handler(alchemy_session, BEFORE_FLUSH)


event.listen(session.Session, AFTER_FLUSH, after_flush_handlers)
event.listen(session.Session, BEFORE_FLUSH, before_flush_handlers)
