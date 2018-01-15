/*
 Copyright (C) 2018 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

(function (GGRC, _) {
  'use strict';
  /**
   * Tree View Widgets Configuration module
   */
  let allCoreTypes = [
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
    'Risk',
    'Section',
    'Standard',
    'System',
    'Threat',
    'Vendor',
  ];
  // NOTE: Widgets that have the order value are sorted by an increase values,
  // the rest of widgets are sorted alphabetically
  let defaultOrderTypes = {
    Standard: 10,
    Regulation: 20,
    Section: 30,
    Objective: 40,
    Control: 50,
    Product: 60,
    System: 70,
    Process: 80,
    Audit: 90,
    Person: 100,
  };
  // Items allowed for mapping via snapshot.
  let snapshotWidgetsConfig = GGRC.config.snapshotable_objects || [];
  let objectVersions = _.map(snapshotWidgetsConfig, function (obj) {
    return obj + '_versions';
  });

  // Items allowed for relationship mapping
  let excludeMappingConfig = [
    'AssessmentTemplate',
    'Evidence',
  ];
  // Extra Tree View Widgets require to be rendered on Audit View
  let auditInclusion = [
    'Assessment',
    'Person',
    'Program',
    'Issue',
    'Evidence',
  ];
  let baseWidgetsByType;

  let filteredTypes = _.difference(allCoreTypes, excludeMappingConfig);
  // Audit is excluded and created a separate logic for it

  let objectVersionWidgets = {};
  snapshotWidgetsConfig.forEach(function (model) {
    objectVersionWidgets[model + '_versions'] = [model];
  });

  baseWidgetsByType = {
    AccessGroup: _.difference(filteredTypes, ['AccessGroup']),
    Audit: [].concat(snapshotWidgetsConfig, excludeMappingConfig,
      auditInclusion).sort(),
    Clause: _.difference(filteredTypes, ['Clause']),
    Contract: _.difference(filteredTypes,
      ['Contract', 'Policy', 'Regulation', 'Standard']),
    Control: filteredTypes,
    Assessment: snapshotWidgetsConfig.concat(
      ['Audit', 'Issue', 'Evidence']).sort(),
    AssessmentTemplate: ['Audit'],
    DataAsset: filteredTypes,
    Evidence: ['Audit', 'Assessment'],
    Facility: filteredTypes,
    Issue: objectVersions.concat(filteredTypes),
    Market: filteredTypes,
    Objective: filteredTypes,
    OrgGroup: filteredTypes,
    Person: ['Evidence'].concat(_.difference(filteredTypes, ['Person'])),
    Policy: _.difference(filteredTypes,
      ['Contract', 'Policy', 'Regulation', 'Standard']),
    Process: filteredTypes,
    Product: filteredTypes,
    Program: _.difference(filteredTypes, ['Program']),
    Project: filteredTypes,
    Regulation: _.difference(filteredTypes,
      ['Contract', 'Policy', 'Regulation', 'Standard']),
    Section: filteredTypes,
    Standard: _.difference(filteredTypes,
      ['Contract', 'Policy', 'Regulation', 'Standard']),
    System: filteredTypes,
    Risk: filteredTypes,
    Threat: filteredTypes,
    Vendor: filteredTypes,
  };

  baseWidgetsByType = _.extend(baseWidgetsByType, objectVersionWidgets);

  GGRC.tree_view = GGRC.tree_view || new can.Map();
  GGRC.tree_view.attr('base_widgets_by_type', baseWidgetsByType);
  GGRC.tree_view.attr('defaultOrderTypes', defaultOrderTypes);
  GGRC.tree_view.attr('basic_model_list', []);
  GGRC.tree_view.attr('sub_tree_for', {});
})(window.GGRC, window._);
