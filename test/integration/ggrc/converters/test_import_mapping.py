# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Test imports of mappings between objects"""

from collections import OrderedDict
import mock

import ddt

from ggrc.utils import title_from_camelcase
from integration.ggrc import TestCase, READONLY_MAPPING_PAIRS
from integration.ggrc import factories


@ddt.ddt
class TestImportMappings(TestCase):
  """Test import mapping/unmapping"""

  def setUp(self):
    super(TestImportMappings, self).setUp()
    self.client.get("/login")

  @ddt.data(*READONLY_MAPPING_PAIRS)
  @ddt.unpack
  def test_unmap_objects(self, model1, model2):
    """Test deprecated unmapping between {0.__name__} and {1.__name__}
    """
    name1 = model1.__name__
    name2 = model2.__name__
    title1 = title_from_camelcase(name1)

    with factories.single_commit():
      with mock.patch('ggrc.login.is_external_app_user', return_value=True):
        obj1 = factories.get_model_factory(name1)()
        obj2 = factories.get_model_factory(name2)()
        factories.RelationshipFactory(source=obj1, destination=obj2,
                                      is_external=True)
        slug1 = obj1.slug
        slug2 = obj2.slug

    data_block = [
        OrderedDict([
            ("object_type", name1),
            ("Code*", slug1),
        ]),
        OrderedDict([
            ("object_type", name2),
            ("Code*", slug2),
            ("unmap:{}".format(title1), slug1),
        ]),
    ]

    response = self.import_data(*data_block)

    # Check that mapping is not added
    self.assertEqual(len(response[1]['row_warnings']), 1)
    self.assertIn(
        u'Line 7: You do not have the necessary permissions to unmap',
        response[1]['row_warnings'][0])
