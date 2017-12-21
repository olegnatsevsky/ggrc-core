/*
 Copyright (C) 2018 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

import template from './templates/tree-item-custom-attribute.mustache';

const formatValueMap = {
  'Checkbox'(item) {
    return ['No', 'Yes'][item.attr('attribute_value')];
  },
  'Date'(item) {
    return GGRC.Utils.formatDate(item.attr('attribute_value'), true);
  },
};

const defaultValueMap = {
  Checkbox: 'No',
};

const _prepareCAVs = (instance) => {
  instance.attr('custom_attribute_values').forEach((cav, index) => {
    instance.custom_attribute_values.attr(index, cav.reify());
  });
};

const getCustomAttrValue = (attr, instance, options) => {
  let value = '';

  attr = Mustache.resolve(attr);
  instance = Mustache.resolve(instance);

  let definition = GGRC.custom_attr_defs.find((item) => {
    return item.definition_type === instance.class.table_singular &&
      item.title === attr.attr_name;
  });

  if (definition) {
    // reify all CA models (with the exception of the Assessment)
    // to load custom_attribute_id, attribute_value and attribute_object
    if (!(instance instanceof CMS.Models.Assessment)) {
      _prepareCAVs(instance);
    }

    let customAttrItem = _.find(instance.attr('custom_attribute_values'),
      (cav) => {
        return cav.custom_attribute_id === definition.id;
      });

    if (customAttrItem) {
      value = formatValueMap[definition.attribute_type] ?
        formatValueMap[definition.attribute_type](customAttrItem, options) :
        customAttrItem.attr('attribute_value');
    } else {
      value = value || defaultValueMap[definition.attribute_type];
    }
  }

  return value || '';
};


export const viewModel = can.Map.extend({
  instance: null,
  values: [],
  column: {},
});

export const helpers = {
  getCustomAttrValue,
};

export default can.Component.extend({
  tag: 'tree-item-custom-attribute',
  template: template,
  viewModel: viewModel,
  helpers: helpers,
});
