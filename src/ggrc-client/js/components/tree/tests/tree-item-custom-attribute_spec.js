/*
  Copyright (C) 2018 Google Inc.
  Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import {helpers} from './../tree-item-custom-attribute';

describe('helpers.getCustomAttrValue', () => {
  let helper;
  let fakeAttr;
  let fakeInstance;
  let fakeOptions;
  let fakeCustomAttrDefs;
  let origValue;
  let setCustomAttrItem;
  let getCustomAttrItem;
  let actual;
  let customAttrItem;

  beforeAll(() => {
    helper = helpers.getCustomAttrValue;

    fakeCustomAttrDefs = [{
      definition_type: 'control',
      id: 3,
      attribute_type: '',
      title: 'Type',
    },
    {
      definition_type: 'control',
      title: 'CheckBox',
      attribute_type: 'Checkbox',
      id: 4,
    },
    {
      definition_type: 'control',
      title: 'Start Date',
      attribute_type: 'Date',
      id: 5,
    },
    {
      definition_type: 'control',
      title: 'Text',
      attribute_type: 'Text',
      id: 6,
    },
    {
      definition_type: 'control',
      title: 'Rich Text',
      attribute_type: 'Rich Text',
      id: 7,
    },
    {
      definition_type: 'control',
      title: 'Date',
      attribute_type: 'Date',
      id: 9,
    },
    {
      definition_type: 'control',
      title: 'Dropdown',
      attribute_type: 'Dropdown',
      id: 10,
    }];

    origValue = GGRC.custom_attr_defs;
    GGRC.custom_attr_defs = fakeCustomAttrDefs;
    fakeInstance = new can.Map({
      custom_attribute_values: [],
    });

    getCustomAttrItem = (attrValue, attrId, attrType) => {
      return new can.Map({
        attribute_value: attrValue,
        custom_attribute_id: attrId || 3,
        attributeType: attrType,
      });
    };

    setCustomAttrItem = (attrValue, attrId, attrType) => {
      customAttrItem = getCustomAttrItem(attrValue, attrId, attrType);
      fakeInstance.attr('custom_attribute_values.0', customAttrItem);

      spyOn(customAttrItem, 'reify')
        .and.returnValue(customAttrItem);
    };
  });

  afterAll(() => {
    GGRC.custom_attr_defs = origValue;
  });

  beforeEach(() => {
    fakeAttr = {};
    fakeOptions = {};
    fakeInstance.class = {table_singular: 'control'};

    fakeAttr.attr_name = 'Type';
  });

  it('reify() is exec if instance is not an Assessment', () => {
    setCustomAttrItem();
    helper(fakeAttr, fakeInstance, fakeOptions);

    expect(customAttrItem.reify).toHaveBeenCalled();
  });

  it('return correct value if customAttrItem is not undefined', () => {
    setCustomAttrItem('correctValue');

    actual = helper(fakeAttr, fakeInstance, fakeOptions);

    expect(actual).toEqual('correctValue');
  });

  it('return an empty string if customAttrItem is undefined', () => {
    setCustomAttrItem();

    actual = helper(fakeAttr, fakeInstance, fakeOptions);

    expect(actual).toEqual('');
  });

  describe('for CA of Checkbox type', () => {
    const attr = {};

    it('returns empty string when CAD wasn\'t found', () => {
      setCustomAttrItem('10', 3, 'Checkbox');

      actual = helper(attr, fakeInstance, fakeOptions);

      expect(actual).toEqual('');
    });

    it('returns "Yes" for CA of type checkbox with value "1"', () => {
      attr.attr_name = 'CheckBox';
      setCustomAttrItem('1', 4, 'checkbox');

      actual = helper(attr, fakeInstance, fakeOptions);

      expect(actual).toEqual('Yes');
    });

    it('returns "No" for CA of type checkbox with value "0"', () => {
      attr.attr_name = 'CheckBox';
      setCustomAttrItem(0, 4, 'checkbox');

      actual = helper(attr, fakeInstance, fakeOptions);

      expect(actual).toEqual('No');
    });

    it('returns "No" for CA of type checkbox without value', () => {
      attr.attr_name = 'CheckBox';
      setCustomAttrItem(undefined, 4, 'checkbox');

      actual = helper(attr, fakeInstance, fakeOptions);

      expect(actual).toEqual('No');
    });

    it('returns "No" for CA of type checkbox if there are no CA values', () => {
      attr.attr_name = 'CheckBox';
      fakeInstance.attr('custom_attribute_values', []);

      actual = helper(attr, fakeInstance, fakeOptions);

      expect(actual).toEqual('No');
    });
  });

  describe('for CA of Date type', () => {
    const attr = {
    };

    it('returns empty string when CAD wasn\'t found', () => {
      setCustomAttrItem('10', 3, 'Date');

      actual = helper(attr, fakeInstance, fakeOptions);

      expect(actual).toEqual('');
    });

    it('returns formatted date when CAD was found', () => {
      const expected = 'expected date';
      const attrValue = '2017-09-30';
      attr.attr_name = 'Date';
      setCustomAttrItem(attrValue, 9, 'Date');
      spyOn(GGRC.Utils, 'formatDate')
        .and.returnValue(expected);

      actual = helper(attr, fakeInstance, fakeOptions);

      expect(actual).toEqual(expected);
      expect(GGRC.Utils.formatDate)
        .toHaveBeenCalledWith(attrValue, true);
    });

    it('tries to format date for existing CAD and undefined value', () => {
        const expected = 'expected date';
        const attrValue = undefined;
        attr.attr_name = 'Date';
        setCustomAttrItem(attrValue, 9, 'Date');
        spyOn(GGRC.Utils, 'formatDate')
          .and.returnValue(expected);

        actual = helper(attr, fakeInstance, fakeOptions);

        expect(actual).toEqual(expected);
        expect(GGRC.Utils.formatDate)
          .toHaveBeenCalledWith(attrValue, true);
      });
  });

  describe('for CA of Dropdown type', () => {
    const attr = {
    };

    it('returns empty string when CAD wasn\'t found', () => {
      setCustomAttrItem('10', 3, 'Dropdown');

      actual = helper(attr, fakeInstance, fakeOptions);

      expect(actual).toEqual('');
    });

    it('returns attribute value when CAD was found', () => {
      attr.attr_name = 'Dropdown';
      setCustomAttrItem('10', 10, 'Dropdown');

      actual = helper(attr, fakeInstance, fakeOptions);

      expect(actual).toEqual('10');
    });

    it('returns empty string for existing CAD and undefined value', () => {
      attr.attr_name = 'Dropdown';
      setCustomAttrItem(undefined, 10, 'Dropdown');

      actual = helper(attr, fakeInstance, fakeOptions);

      expect(actual).toEqual('');
    });
  });

  describe('for CA of Text type', () => {
    const attr = {
    };

    it('returns empty string when CAD wasn\'t found', () => {
      setCustomAttrItem('10', 3, 'Text');

      actual = helper(attr, fakeInstance, fakeOptions);

      expect(actual).toEqual('');
    });

    it('returns attribute value when CAD was found', () => {
      attr.attr_name = 'Text';
      setCustomAttrItem('10', 6, 'Text');

      actual = helper(attr, fakeInstance, fakeOptions);

      expect(actual).toEqual('10');
    });

    it('returns empty string for existing CAD and undefined value', () => {
      attr.attr_name = 'Text';
      setCustomAttrItem(undefined, 6, 'Text');

      actual = helper(attr, fakeInstance, fakeOptions);

      expect(actual).toEqual('');
    });
  });

  describe('for CA of Rich Text type', () => {
    const attr = {
    };

    it('returns empty string when CAD wasn\'t found', () => {
      setCustomAttrItem('10', 3, 'Rich Text');

      actual = helper(attr, fakeInstance, fakeOptions);

      expect(actual).toEqual('');
    });

    it('returns attribute value when CAD was found', () => {
      attr.attr_name = 'Rich Text';
      setCustomAttrItem('10', 7, 'Rich Text');

      actual = helper(attr, fakeInstance, fakeOptions);

      expect(actual).toEqual('10');
    });

    it('returns empty string for existing CAD and undefined value', () => {
      attr.attr_name = 'Rich Text';
      setCustomAttrItem(undefined, 7, 'Rich Text');

      actual = helper(attr, fakeInstance, fakeOptions);

      expect(actual).toEqual('');
    });
  });
});
