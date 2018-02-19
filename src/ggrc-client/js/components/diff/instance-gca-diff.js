/*
 Copyright (C) 2018 Google Inc., authors, and contributors
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

import {REFRESH_PROPOSAL_DIFF} from '../../events/eventTypes';
import DiffBaseVM from './diff-base-vm';
import template from './templates/instance-diff-items.mustache';
const tag = 'instance-gca-diff';

const viewModel = DiffBaseVM.extend({
  modifiedAttributes: {},
  _customAttributesValues: [],

  prepareAttributes() {
    const values = this.attr('currentInstance.custom_attribute_values')
      .map((value) => value.reify());

    this.attr('_customAttributesValues', values);
  },
  buildDiffObject() {
    const modifiedAttributes = this.attr('modifiedAttributes');
    const caKeys = can.Map.keys(modifiedAttributes);

    this.prepareAttributes();
    this.attr('diff', []);

    caKeys.forEach((attrId) => {
      let attr;
      let modifiedAttr;
      attrId = Number(attrId);

      attr = this.getValueAndDefinition(attrId);
      modifiedAttr = modifiedAttributes[attrId];

      // attr was deleted
      if (!attr.def) {
        return;
      }

      const diffObject = this.buildAttributeDiff(modifiedAttr, attr);
      this.attr('diff').push(diffObject);
    });
  },
  buildAttributeDiff(modifiedAttr, currentAttr) {
    const value = currentAttr.value;
    const def = currentAttr.def;
    let modifiedVal = this.attr('emptyValue');
    let currentVal = this.attr('emptyValue');

    if (value) {
      currentVal = this
        .convertValue(value.attribute_value, def.attribute_type);
    }

    if (modifiedAttr && modifiedAttr.attribute_value) {
      modifiedVal = this
        .convertValue(modifiedAttr.attribute_value, def.attribute_type);
    }

    return {
      attrName: def.title,
      currentVal: [currentVal],
      modifiedVal: [modifiedVal],
    };
  },
  convertValue(value, type) {
    if (!value) {
      return this.attr('emptyValue');
    }

    switch (type) {
      case 'Date':
        return GGRC.Utils.formatDate(value, true);
      case 'Checkbox':
        return value === true || value === '1' ?
          '✓' :
          this.attr('emptyValue');
      default:
        return value;
    }
  },
  getValueAndDefinition(attrId) {
    const instance = this.attr('currentInstance');
    const value = this.attr('_customAttributesValues').attr()
      .find((val) => val.custom_attribute_id === attrId);
    const definition = instance.attr('custom_attribute_definitions').attr()
      .find((def) => def.id === attrId);

    return {
      value: value,
      def: definition,
    };
  },
});

export default can.Component.extend({
  tag,
  template,
  viewModel: viewModel,
  events: {
    buildDiff() {
      const instance = this.viewModel.attr('currentInstance');
      const modifiedCA = this.viewModel.attr('modifiedAttributes');
      if (!modifiedCA || !instance) {
        return;
      }
      this.viewModel.buildDiffObject();
    },
    inserted() {
      this.buildDiff();
    },
    [`{viewModel.currentInstance} ${REFRESH_PROPOSAL_DIFF.type}`]() {
      this.buildDiff();
    },
  },
});
