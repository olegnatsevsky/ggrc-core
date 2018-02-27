/*
 Copyright (C) 2018 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

import '../tree/tree-item-custom-attribute';
import '../tree/tree-field';
import template from './templates/mapper-results-item-attrs.mustache';

(function (can, GGRC) {
  'use strict';

  let DEFAULT_ATTR_TEMPLATE =
    '/static/mustache/base_objects/tree-item-attr.mustache';

  GGRC.Components('mapperResultsItemAttrs', {
    tag: 'mapper-results-item-attrs',
    template: template,
    viewModel: {
      init: function () {
        let Model = CMS.Models[this.attr('modelType')];
        let attrTemplate = Model.tree_view_options.attr_view;
        this.attr('attrTemplate', attrTemplate || DEFAULT_ATTR_TEMPLATE);
      },
      instance: null,
      columns: [],
      modelType: '',
      attrTemplate: DEFAULT_ATTR_TEMPLATE,
    },
    events: {
      click(element, event) {
        if ($(event.target).is('.link')) {
          event.stopPropagation();
        }
      },
    },
  });
})(window.can, window.GGRC);
