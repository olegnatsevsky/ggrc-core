# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""GDrive module"""

import flask
import google.oauth2.credentials
from google_auth_oauthlib.helpers import credentials_from_session
from requests_oauthlib import OAuth2Session

from werkzeug.exceptions import BadRequest

from ggrc import settings
from ggrc.app import app

_GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
_GOOGLE_TOKEN_URI = "https://accounts.google.com/o/oauth2/token"
_GOOGLE_API_GDRIVE_SCOPE = "https://www.googleapis.com/auth/drive"


class UserCredentialException(Exception):
  pass


def get_credentials():
  if 'credentials' not in flask.session:
    raise UserCredentialException('User credentials not found.')
  credentials = google.oauth2.credentials.Credentials(
      **flask.session['credentials'])
  return credentials


def verify_credentials():
  """Verify credentials to gdrive for the current user

  :return: None, if valid credentials are present, or redirect to authorize fn
  """
  if 'credentials' not in flask.session:
    return authorize_gdrive()
  credentials = google.oauth2.credentials.Credentials(
      **flask.session['credentials'])
  if credentials.expired:
    return authorize_gdrive()
  return None


@app.route("/authorize_gdrive")
def authorize_gdrive():
  """1st step of oauth2 flow"""
  google_session = OAuth2Session(settings.GAPI_CLIENT_ID,
                                 scope=[_GOOGLE_API_GDRIVE_SCOPE],
                                 redirect_uri=flask.url_for('authorize',
                                                            _external=True))
  authorization_url, state = google_session.authorization_url(_GOOGLE_AUTH_URI)
  flask.session['state'] = state

  ggrc_view_to_redirect = flask.request.url
  if flask.request.path == flask.url_for('authorize_gdrive'):
      ggrc_view_to_redirect = flask.request.host_url
  flask.session['ggrc_view_to_redirect'] = ggrc_view_to_redirect

  return flask.redirect(authorization_url)


@app.route('/authorize')
def authorize():
  """Callback used for 2nd step of oauth2 flow"""
  if ('ggrc_view_to_redirect' not in flask.session or
          'state' not in flask.session):
    raise BadRequest(
        "Don't call /authorize directly. It used for authorization callback")

  # Specify the state when creating the flow in the callback so that it can
  # verified in the authorization server response.
  state = flask.session['state']

  authorization_response = flask.request.url

  google_session = OAuth2Session(settings.GAPI_CLIENT_ID,
                                 state=state,
                                 scope=[_GOOGLE_API_GDRIVE_SCOPE],
                                 redirect_uri=flask.url_for('authorize',
                                                            _external=True))
  google_session.fetch_token(_GOOGLE_TOKEN_URI,
                             client_secret=settings.GAPI_CLIENT_SECRET,
                             authorization_response=authorization_response)

  # Store credentials in the session.
  # ACTION ITEM: To save these credentials in a persistent database instead.
  credentials = credentials_from_session(google_session)
  flask.session['credentials'] = credentials_to_dict(credentials)
  del flask.session['state']
  ggrc_view_to_redirect = flask.session['ggrc_view_to_redirect']
  return flask.redirect(ggrc_view_to_redirect)


def credentials_to_dict(credentials):
  return {
      'token': credentials.token,
      'refresh_token': credentials.refresh_token,
      'token_uri': credentials.token_uri,
      'client_id': credentials.client_id,
      'client_secret': credentials.client_secret,
      'scopes': credentials.scopes
  }
