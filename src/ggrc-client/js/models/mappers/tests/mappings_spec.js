/*
 Copyright (C) 2018 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

import {getInScopeModels} from '../../../plugins/utils/snapshot-utils';

describe('GGRC.Mappings', function () {
  'use strict';

  let allTypes = [];
  let notMappableModels = [];
  let modules = {
    core: {
      models: [
        'AccessGroup',
        'Assessment',
        'AssessmentTemplate',
        'Audit',
        'Clause',
        'Contract',
        'Control',
        'DataAsset',
        'Evidence',
        'Facility',
        'Issue',
        'Market',
        'Objective',
        'OrgGroup',
        'Person',
        'Policy',
        'Process',
        'Product',
        'Program',
        'Project',
        'Regulation',
        'Section',
        'Standard',
        'System',
        'Vendor',
        'Risk',
        'Threat',
      ],
      notMappable: ['Assessment', 'AssessmentTemplate', 'Evidence'],
    },
    risk_assessments: {
      models: ['RiskAssessment'],
      notMappable: ['RiskAssessment'],
    },
    workflows: {
      models: [
        'TaskGroup',
        'Workflow',
        'CycleTaskEntry',
        'CycleTaskGroupObjectTask',
        'CycleTaskGroupObject',
        'CycleTaskGroup',
      ],
      notMappable: [
        'CycleTaskEntry',
        'CycleTaskGroupObjectTask',
        'CycleTaskGroupObject',
        'CycleTaskGroup',
      ],
    },
  };
  let directives = ['Contract', 'Policy', 'Regulation', 'Standard'];
  let mappingRules;
  let filtered;

  function getModelsFromGroups(groups, groupNames) {
    let models = [];
    groupNames.forEach(function (groupName) {
      let groupModels = groups[groupName].items.map(function (item) {
        return item.singular;
      });
      models = models.concat(groupModels);
    });
    return models;
  }

  Object.keys(modules).forEach(function (module) {
    allTypes = allTypes.concat(modules[module].models);
    notMappableModels = notMappableModels.concat(modules[module].notMappable);
  });

  filtered = _.difference(allTypes, notMappableModels);

  mappingRules = {
    AccessGroup: _.difference(filtered, ['AccessGroup']),
    Assessment: _.difference(filtered, ['Audit', 'Person', 'Program', 'Project',
      'TaskGroup', 'Workflow']),
    AssessmentTemplate: _.difference(filtered, ['Audit', 'Person', 'Program',
      'Project', 'TaskGroup', 'Workflow']),
    Audit: _.difference(filtered, ['Audit', 'Person', 'Program', 'Project',
      'TaskGroup', 'Workflow']),
    Clause: _.difference(filtered, ['Clause']),
    Contract: _.difference(filtered, directives),
    Control: filtered,
    CycleTaskGroupObjectTask: _.difference(filtered, ['Person',
      'TaskGroup', 'Workflow']),
    DataAsset: filtered,
    Evidence: ['Assessment', 'Audit'],
    Facility: filtered,
    Issue: _.difference(filtered, ['Audit', 'Person', 'Workflow']),
    Market: filtered,
    Objective: filtered,
    OrgGroup: filtered,
    Person: _.difference(filtered, ['Person', 'Audit', 'TaskGroup',
      'Workflow', 'Issue']),
    Policy: _.difference(filtered, directives),
    Process: filtered,
    Product: filtered,
    Program: _.difference(allTypes,
      ['Program', 'Audit', 'RiskAssessment'].concat(modules.core.notMappable,
      modules.workflows.notMappable)),
    Project: filtered,
    Regulation: _.difference(filtered, directives),
    Risk: filtered,
    RiskAssessment: [],
    Section: filtered,
    Standard: _.difference(filtered, directives),
    System: filtered,
    TaskGroup: _.difference(filtered, ['Audit', 'Person',
      'TaskGroup', 'Workflow']),
    Threat: filtered,
    Vendor: filtered,
  };

  beforeAll(function () {
    // init all modules
    can.each(GGRC.extensions, function (extension) {
      if (modules[extension.name] && extension.init_widgets) {
        extension.init_widgets();
      }
    });
  });

  describe('getMappingTypes() method', function () {
    let EXPECTED_GROUPS = ['entities', 'business', 'governance'];
    let modelsForTests = _.difference(allTypes, [
      'CycleTaskEntry',
      'CycleTaskGroup',
      'CycleTaskGroupObject',
      'Workflow',
    ]);

    modelsForTests.forEach(function (type) {
      it('returns mappable types for ' + type, function () {
        let expectedModels = mappingRules[type];
        let result = GGRC.Mappings.getMappingTypes(type, [], getInScopeModels());
        let resultGroups = Object.keys(result);
        let resultModels = getModelsFromGroups(result, EXPECTED_GROUPS);

        expect(EXPECTED_GROUPS).toEqual(resultGroups);
        expect(expectedModels.sort()).toEqual(resultModels.sort());
      });
    });
  });

  describe('_prepareCorrectTypeFormat() method', function () {
    let cmsModel = {
      category: 'category',
      title_plural: 'title_plural',
      model_singular: 'model_singular',
      table_plural: 'table_plural',
      title_singular: 'title_singular',
    };
    let expectedResult = {
      category: 'category',
      name: 'title_plural',
      value: 'model_singular',
      plural: 'title_plural',
      singular: 'model_singular',
      table_plural: 'table_plural',
      title_singular: 'title_singular',
    };

    it('returns specified object', function () {
      let result;
      result = GGRC.Mappings._prepareCorrectTypeFormat(cmsModel);
      expect(result).toEqual(expectedResult);
    });

    it('converts models plural title to a snake_case', function () {
      let result;
      let cmsModel1 = _.assign({}, cmsModel, {
        title_plural: 'Title Plural',
      });
      result = GGRC.Mappings._prepareCorrectTypeFormat(cmsModel1);
      expect(result.plural).toEqual(expectedResult.plural);
    });
  });

  describe('addFormattedType() method', function () {
    let groups;
    let type = {
      category: 'category',
    };

    beforeEach(function () {
      groups = {
        governance: {
          items: [],
        },
        category: {
          items: [],
        },
      };
      spyOn(GGRC.Mappings, '_prepareCorrectTypeFormat')
        .and.returnValue(type);
    });

    it('adds type to governance group if no group with category of this type',
      function () {
        groups.category = undefined;
        spyOn(GGRC.Utils, 'getModelByType')
          .and.returnValue({
            title_singular: 'title_singular',
          });
        GGRC.Mappings._addFormattedType('name', groups);
        expect(groups.governance.items[0]).toEqual(type);
      });

    it('adds type to group of category of this type if this group exist',
      function () {
        groups.governance = undefined;
        spyOn(GGRC.Utils, 'getModelByType')
          .and.returnValue({
            title_singular: 'title_singular',
          });
        GGRC.Mappings._addFormattedType('name', groups);
        expect(groups[type.category].items[0]).toEqual(type);
      });

    it('does nothing if cmsModel is not defined', function () {
      spyOn(GGRC.Utils, 'getModelByType');
      GGRC.Mappings._addFormattedType('name', groups);
      expect(groups.governance.items.length).toEqual(0);
      expect(groups[type.category].items.length).toEqual(0);
    });
    it('does nothing if singular title of cmsModel is not defined',
      function () {
        spyOn(GGRC.Utils, 'getModelByType')
          .and.returnValue({});
        GGRC.Mappings._addFormattedType('name', groups);
        expect(groups.governance.items.length).toEqual(0);
        expect(groups[type.category].items.length).toEqual(0);
      });
    it('does nothing if singular title of cmsModel is "Reference"',
      function () {
        spyOn(GGRC.Utils, 'getModelByType')
          .and.returnValue({
            title_singular: 'Reference',
          });
        GGRC.Mappings._addFormattedType('name', groups);
        expect(groups.governance.items.length).toEqual(0);
        expect(groups[type.category].items.length).toEqual(0);
      });
  });
});
