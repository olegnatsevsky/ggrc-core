# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""GDrive module"""

import flask
import google.oauth2.credentials
import google_auth_oauthlib.flow

from werkzeug.exceptions import BadRequest

from ggrc import settings
from ggrc.app import app

_GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
_GOOGLE_TOKEN_URI = "https://accounts.google.com/o/oauth2/token"
_GOOGLE_API_GDRIVE_SCOPE = "https://www.googleapis.com/auth/drive"

CLIENT_CONFIG = {
    u'web': {
        u'token_uri': _GOOGLE_TOKEN_URI,
        u'auth_uri': _GOOGLE_AUTH_URI,
        u'client_id': settings.GAPI_CLIENT_ID,
        u'client_secret': settings.GAPI_CLIENT_SECRET,
    }
}


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
  flow = google_auth_oauthlib.flow.Flow.from_client_config(
      CLIENT_CONFIG, scopes=[_GOOGLE_API_GDRIVE_SCOPE])
  flow.redirect_uri = flask.url_for('authorize', _external=True)

  authorization_url, state = flow.authorization_url(
      # Enable incremental authorization. Recommended as a best practice.
      include_granted_scopes='true')
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

  flow = google_auth_oauthlib.flow.Flow.from_client_config(
      CLIENT_CONFIG, scopes=[_GOOGLE_API_GDRIVE_SCOPE], state=state)
  flow.redirect_uri = flask.url_for('authorize', _external=True)
  authorization_response = flask.request.url
  flow.fetch_token(authorization_response=authorization_response)

  # Store credentials in the session.
  # ACTION ITEM: To save these credentials in a persistent database instead.
  credentials = flow.credentials
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
