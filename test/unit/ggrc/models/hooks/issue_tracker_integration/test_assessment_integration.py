# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Test issue_tracker hooks."""

import unittest

import ddt
import mock

from ggrc.models import all_models
from ggrc.models.hooks.issue_tracker import assessment_integration
from ggrc.integrations import integrations_errors
from ggrc.models.hooks.issue_tracker import integration_utils


@ddt.ddt
class TestUtilityFunctions(unittest.TestCase):
  """Test utility function in issue_tracker module."""

  ISSUE_TRACKED_NAMESPACE = \
      "ggrc.models.hooks.issue_tracker.assessment_integration"

  def setUp(self):
    super(TestUtilityFunctions, self).setUp()
    self.session = mock.MagicMock()

  @ddt.data(
      ({'component_id': '1111', 'hotlist_id': '2222'},
       None,),
      ({'component_id': '1111'},
       None,),
      ({'hotlist_id': '2222'},
       None,),
      ({'component_id': 'zzz'},
       integration_utils.exceptions.ValidationError,),
      ({'hotlist_id': 'zzz'},
       integration_utils.exceptions.ValidationError,),
  )
  @ddt.unpack
  def test_validate_info(self, info, expected_error):
    """Test _validate_issue_tracker_info function."""
    initial_info = dict(info)
    # pylint: disable=protected-access
    if expected_error:
      with self.assertRaises(expected_error):
        integration_utils.validate_issue_tracker_info(info)
    else:
      integration_utils.validate_issue_tracker_info(info)

    self.assertEqual(info, initial_info)

  @ddt.data(
      ({'component_id': '1111', 'hotlist_id': '2222'},
       {'component_id': 1111, 'hotlist_id': 2222},
       None,),
      ({'component_id': '1111'},
       {'component_id': 1111},
       None,),
      ({'hotlist_id': '2222'},
       {'hotlist_id': 2222},
       None,),
      ({'component_id': 'zzz'},
       None,
       integration_utils.exceptions.ValidationError,),
      ({'hotlist_id': 'zzz'},
       None,
       integration_utils.exceptions.ValidationError,),
  )
  @ddt.unpack
  def test_normalize_info(self, info, expected, expected_error):
    """Test _normalize_issue_tracker_info function."""
    # pylint: disable=protected-access
    if expected_error:
      with self.assertRaises(expected_error):
        integration_utils.normalize_issue_tracker_info(info)
    else:
      integration_utils.normalize_issue_tracker_info(info)
      self.assertEqual(info, expected)

  @mock.patch(ISSUE_TRACKED_NAMESPACE + '._is_issue_tracker_enabled',
              lambda audit: True)
  @ddt.data((True, 123), (False, 123))
  @ddt.unpack
  def test_issue_tracker_error(self, issue_tracker_enabled, issue_id):
    """ Test that issue tracker does not change state
        in case receiving an error."""
    with mock.patch(self.ISSUE_TRACKED_NAMESPACE +
                    '._update_issuetracker_issue') as update_issue_mock, \
        mock.patch(self.ISSUE_TRACKED_NAMESPACE +
                   '._update_issuetracker_info') as update_info_mock, \
        mock.patch(self.ISSUE_TRACKED_NAMESPACE + '._collect_issue_emails',
                   side_effect=[(None, [])]):
      error_data = integrations_errors.HttpError('data')
      update_issue_mock.side_effect = error_data
      src = {
          'issue_tracker': {
              'enabled': issue_tracker_enabled,
              'issue_id': issue_id
          }
      }
      all_models.IssuetrackerIssue.get_issue = mock.MagicMock()
      # pylint: disable=protected-access
      assessment_integration._handle_issuetracker(sender=None,
                                                  obj=mock.MagicMock(),
                                                  src=src)
      update_info_mock.assert_called_once()
      self.assertEqual(update_info_mock.call_args[0][1]['enabled'],
                       issue_tracker_enabled)
