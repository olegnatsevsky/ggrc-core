# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Handlers evidence entries."""

from logging import getLogger

from ggrc import models
from ggrc.converters import errors
from ggrc.converters.handlers import handlers
from ggrc.login import get_current_user_id


# pylint: disable=invalid-name
logger = getLogger(__name__)


class EvidenceLinkHandler(handlers.ColumnHandler):
  """Base class for document documents handlers."""

  KIND = None

  @staticmethod
  def _parse_line(line):
    raise NotImplemented()

  def _get_old_map(self):
    raise NotImplemented()

  def get_value(self):
    raise NotImplemented()

  def build_evidence(self, link, title, user_id):
    evidence = models.Evidence(
        link=link,
        title=title,
        modified_by_id=user_id,
        context=self.row_converter.obj.context,
        kind=self.KIND,
    )
    return evidence

  def parse_item(self, has_title=False):
    """Parse evidence link lines.

    Returns:
      list of evidences for all URLs and evidences.
    """
    new_links = set()
    duplicate_new_links = set()

    evidences = []
    user_id = get_current_user_id()

    for line in self.raw_value.splitlines():
      link, title = self._parse_line(line)
      if not (link and title):
        continue

      if link in new_links:
        duplicate_new_links.add(link)
      else:
        new_links.add(link)
        evidences.append(self.build_evidence(link, title, user_id))

    if duplicate_new_links:
      # NOTE: We rely on the fact that links in duplicate_new_links are all
      # instances of unicode (if that assumption breaks, unicode encode/decode
      # errors can occur for non-ascii link values)
      self.add_warning(errors.DUPLICATE_IN_MULTI_VALUE,
                       column_name=self.display_name,
                       duplicates=u", ".join(sorted(duplicate_new_links)))

    return evidences

  def set_obj_attr(self):
    self.value = self.parse_item()

  def set_value(self):
    """This should be ignored with second class attributes."""

  def insert_object(self):
    """Update document URL values

    This function adds missing URLs and remove existing ones from Documents.
    The existing URLs with new titles just change the title.
    """
    if self.row_converter.ignore:
      return
    new_link_map = {d.link: d for d in self.value}
    old_link_map = self._get_old_map()

    for new_link, new_evid in new_link_map.iteritems():
      if new_link in old_link_map:
        old_link_map[new_link].title = new_evid.title
      else:
        models.Relationship(source=self.row_converter.obj, destination=new_evid)

    for old_link, old_doc in old_link_map.iteritems():
      if old_link in new_link_map:
        continue
      if old_doc.related_destinations:
        old_doc.related_destinations.pop()
      elif old_doc.related_sources:
        old_doc.related_sources.pop()
      else:
        logger.warning("Invalid relationship state for document URLs.")


class EvidenceFileHandler(EvidenceLinkHandler):
  """Handler for evidence of type file on evidence imports."""

  KIND = models.Evidence.FILE

  @staticmethod
  def get_gdrive_id_from_url(url):
    """Extract gdrive_id from URL

    based on url slicing:
                                   |                            |
    https://drive.google.com/file/d/0B7PUdT4q_eqpeXRLb25tU3VfNzQ/view?usp=drivesdk
    or                              |                            |
    https://drive.google.com/open?id=0Bx9jGVp6d-sfN1pOZlZzbHF2QVU/view
    """
    result = ''
    try:
      if '?id=' in url:
        result = url.split('?id=')[1].split('&')[0]
      elif '/d/' in url:
        result = url.split('/d/')[1].split('/')[0]
    except IndexError:
      pass
    return result

  def get_gdrive_id(self, link):
    """Handle gdrive_id extraction"""
    gdrive_id = self.get_gdrive_id_from_url(link)
    if not gdrive_id:
      self.add_warning(errors.UNABLE_TO_EXTRACT_GDRIVE_ID,
                       link=link)
    return gdrive_id

  def build_evidence(self, link, title, user_id):
    evidence = models.Evidence(
        link=link,
        title=title,
        modified_by_id=user_id,
        context=self.row_converter.obj.context,
        kind=self.KIND,
        gdrive_id=self.get_gdrive_id(link),
        source_gdrive_id=''
    )
    return evidence

  @staticmethod
  def _parse_line(line):
    """Parse a single line and return link and title.

    Args:
      line: string containing a single line from a cell.

    Returns:
      tuple containing a link and a title.
    """
    parts = line.strip().split()
    return parts[0], parts[0] if len(parts) == 1 else " ".join(parts[1:])

  def get_value(self):
    """Generate a new line separated string for all document links.

    Returns:
      string containing all evidence URLs and titles.
    """
    return u"\n".join(u"{} {}".format(d.link, d.title) for d in
                      self.row_converter.obj.evidences_file)

  def _get_old_map(self):
    return {d.link: d for d in self.row_converter.obj.evidences_file}


class EvidenceUrlHandler(EvidenceLinkHandler):
  """Handler for URL field on document imports."""

  KIND = models.Evidence.URL

  @staticmethod
  def _parse_line(line):
    """Parse a single line and return link and title.

    Args:
      line: string containing a single line from a cell.

    Returns:
      tuple containing a link and a title.
    """
    return [line.strip()] * 2

  def _get_old_map(self):
    return {d.link: d for d in self.row_converter.obj.evidences_url}

  def get_value(self):
    """Generate a new line separated string for all document links.

    Returns:
      string containing all URLs
    """
    return "\n".join(doc.link for doc in self.row_converter.obj.evidences_url)
