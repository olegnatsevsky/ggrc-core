# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Main view functions for import and export pages.

This module handles all view related function to import and export pages
including the import/export api endponts.
"""

from logging import getLogger

from googleapiclient.errors import HttpError

from flask import current_app
from flask import request
from flask import json
from flask import render_template
from werkzeug.exceptions import (
    BadRequest, InternalServerError, Unauthorized
)

from ggrc import settings
from ggrc.gdrive import verify_credentials
from ggrc.gdrive import file_actions as fa
from ggrc.app import app
from ggrc.converters.base import Converter
from ggrc.converters.import_helper import generate_csv_string
from ggrc.query.exceptions import BadQueryException
from ggrc.query.builder import QueryHelper
from ggrc.login import login_required
from ggrc.utils import benchmark


# pylint: disable=invalid-name
logger = getLogger(__name__)


def check_required_headers(required_headers):
  """Check required headers to the current request"""
  errors = []
  for header, valid_values in required_headers.items():
    if header not in request.headers:
      errors.append("Missing required header '{}'".format(header))
    elif request.headers[header] not in valid_values:
      errors.append("Invalid header value for '{}'".format(header))

  if errors:
    raise BadRequest("\n".join(errors))


def parse_export_request():
  """ Check if request contains all required fields """
  required_headers = {
      "X-Requested-By": ["GGRC"],
      "Content-Type": ["application/json"],
      "X-export-view": ["blocks", "grid"],
  }
  check_required_headers(required_headers)
  return request.json


def handle_export_request():
  """Export request handler"""
  # pylint: disable=too-many-locals
  try:
    with benchmark("handle export request data"):
      data = parse_export_request()
      objects = data.get("objects")
      export_to = data.get("export_to")
      current_time = data.get("current_time")
      query_helper = QueryHelper(objects)
      ids_by_type = query_helper.get_ids()
    with benchmark("Generate CSV array"):
      converter = Converter(ids_by_type=ids_by_type)
      csv_data = converter.to_array()
    with benchmark("Generate CSV string"):
      csv_string = generate_csv_string(csv_data)
    with benchmark("Make response."):
      object_names = "_".join(converter.get_object_names())
      filename = "{}_{}.csv".format(object_names, current_time)
      if export_to == "gdrive":
        gfile = fa.create_gdrive_file(csv_string, filename)
        headers = [('Content-Type', 'application/json'), ]
        return current_app.make_response((json.dumps(gfile), 200, headers))
      if export_to == "csv":
        headers = [
            ("Content-Type", "text/csv"),
            ("Content-Disposition",
             "attachment; filename='{}'".format(filename)),
        ]
        return current_app.make_response((csv_string, 200, headers))
  except BadQueryException as exception:
    raise BadRequest(exception.message)
  except HttpError as e:
    message = json.loads(e.content).get("error").get("message")
    if e.resp.code == 401:
      raise Unauthorized("{} Try to reload /export page".format(message))
    raise InternalServerError(message)
  except Exception as e:  # pylint: disable=broad-except
    logger.exception("Export failed: %s", e.message)
    raise InternalServerError("Export failed due to internal server error.")


def check_import_file():
  """Check if imported file format and type is valid"""
  if "file" not in request.files or not request.files["file"]:
    raise BadRequest("Missing csv file")
  csv_file = request.files["file"]
  if not csv_file.filename.lower().endswith(".csv"):
    raise BadRequest("Invalid file type.")
  return csv_file


def parse_import_request():
  """ Check if request contains all required fields """
  required_headers = {
      "X-Requested-By": ["GGRC"],
      "X-test-only": ["true", "false"],
  }
  check_required_headers(required_headers)
  try:
    file_data = request.json
    dry_run = request.headers["X-test-only"] == "true"
    return dry_run, file_data
  except:  # pylint: disable=bare-except
    raise BadRequest("Export failed due incorrect request data.")


def handle_import_request():
  """Import request handler"""
  dry_run, file_data = parse_import_request()
  csv_data = fa.get_gdrive_file(file_data)
  try:
    converter = Converter(dry_run=dry_run, csv_data=csv_data)
    converter.import_csv()
    response_data = converter.get_info()
    response_json = json.dumps(response_data)
    headers = [("Content-Type", "application/json")]
    return current_app.make_response((response_json, 200, headers))
  except:  # pylint: disable=bare-except
    logger.exception("Import failed")
  raise BadRequest("Import failed due to server error.")


def init_converter_views():
  """Initialize views for import and export."""

  # pylint: disable=unused-variable
  # The view function trigger a false unused-variable.
  @app.route("/_service/export_csv", methods=["POST"])
  @login_required
  def handle_export_csv():
    """Calls export handler"""
    with benchmark("handle export request"):
      return handle_export_request()

  @app.route("/_service/import_csv", methods=["POST"])
  @login_required
  def handle_import_csv():
    """Calls import handler"""
    with benchmark("handle import request"):
      return handle_import_request()

  @app.route("/import")
  @login_required
  def import_view():
    """Get import view"""
    if getattr(settings, "GAPI_CLIENT_ID", None):
      authorize = verify_credentials()
      if authorize:
        return authorize
    return render_template("import_export/import.haml")

  @app.route("/export")
  @login_required
  def export_view():
    """Get export view"""
    if getattr(settings, "GAPI_CLIENT_ID", None):
      authorize = verify_credentials()
      if authorize:
        return authorize
    return render_template("import_export/export.haml")
