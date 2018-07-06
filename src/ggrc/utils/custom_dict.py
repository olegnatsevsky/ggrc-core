# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Module contains customized dictionaries """

from UserDict import UserDict


class MissingKeyDict(UserDict):
  """Dictionary return missing key as value"""
  def __missing__(self, key):
    return key
