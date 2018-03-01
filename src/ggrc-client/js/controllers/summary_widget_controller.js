/*
    Copyright (C) 2018 Google Inc.
    Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import '../components/add-object-button/add-object-button';
import '../components/assessment_generator';
import {
  getCounts,
} from '../plugins/utils/current-page-utils';
import router from '../router';
import {
  getDefaultStatesForModel,
} from '../plugins/utils/state-utils';

export default can.Control({
  defaults: {
    model: null,
    instance: null,
    widget_view: GGRC.mustache_path + '/base_objects/summary.mustache',
    isLoading: true,
    isShown: false,
    forceRefresh: false,
    colorsMap: {
      'Completed and Verified': '#009925',
      'Completed (no verification)': '#405f77',
      Deprecated: '#704c70',
      'In Progress': '#3369e8',
      'Not Started': '#9e9e9e',
      'In Review': '#f57c00',
      'Rework Needed': '#d50f25',
    },
    chartOptions: {
      pieSliceText: 'value-and-percentage',
      chartArea: {
        width: '100%',
        height: '90%',
      },
      height: 300,
      legend: {
        position: 'none',
      },
    },
  },
  init: function () {
    let that = this;
    $(function () {
      if (GGRC.page_object) {
        $.extend(that.defaults, {
          model: GGRC.infer_object_type(GGRC.page_object),
          instance: GGRC.page_instance(),
        });
      }
    });
  },
}, {
  init: function () {
    let frag;
    if (this.element.data('widget-view')) {
      this.options.widget_view = GGRC.mustache_path +
        this.element.data('widget-view');
    }
    this.element.closest('.widget')
      .on('widget_shown', this.widget_shown.bind(this));
    this.element.closest('.widget')
      .on('widget_hidden', this.widget_hidden.bind(this));
    this.options.context = new can.Map({
      model: this.options.model,
      instance: this.options.instance,
      error_msg: '',
      error: true,
      charts: {
        Assessment: {
          legend: [],
        },
      },
    });
    frag = can.view(this.get_widget_view(this.element),
      this.options.context);
    this.widget_shown();
    this.element.html(frag);
    return 0;
  },
  onRelationshipChange: function (model, ev, instance) {
    if (instance instanceof CMS.Models.Relationship &&
    instance.attr('destination.type') === 'Evidence' &&
    instance.attr('source.type') === 'Assessment') {
      this.options.forceRefresh = true;
    }
  },
  '{CMS.Models.Relationship} destroyed': 'onRelationshipChange',
  '{CMS.Models.Relationship} created': 'onRelationshipChange',
  '{CMS.Models.Assessment} updated': function (model, ev, instance) {
    if (instance instanceof CMS.Models.Assessment) {
      this.options.forceRefresh = true;
    }
  },
  get_widget_view: function (el) {
    let widgetView = $(el)
      .closest('[data-widget-view]')
      .attr('data-widget-view');
    return (widgetView && widgetView.length > 0) ?
      GGRC.mustache_path + widgetView :
      this.options.widget_view;
  },
  widget_shown: function (event) {
    this.options.isShown = true;
    setTimeout(this.reloadSummary.bind(this), 0);

    $(window).trigger('resize');
    return false;
  },
  widget_hidden: function (event) {
    this.options.isShown = false;
    return false;
  },
  reloadSummary: function () {
    let that = this;
    this.loadChartLibrary(function () {
      that.reloadChart('Assessment', 'piechart_audit_assessments_chart');
    });
  },
  reloadChart: function (type, elementId) {
    let that = this;
    let chartOptions = this.options.context.charts[type];
    // Note that chart will be refreshed only if counts were changed.
    // State changes are not checked.
    let countsChanged =
      getCounts().attr(type) !== chartOptions.attr('total.assessments');

    if (chartOptions.attr('isInitialized') && !countsChanged &&
    !this.options.forceRefresh) {
      return;
    }
    this.options.forceRefresh = false;
    chartOptions.attr('isInitialized', true);

    that.setState(type, {total: 0, statuses: { }}, true);
    that.getStatuses(that.options.instance.id).then(function (raw) {
      let data = that.parseStatuses(type, raw);
      let chart = that.drawChart(elementId, data);

      that.prepareLegend(type, chart, data);
      that.setState(type, data, false);
    });
  },
  drawChart: function (elementId, raw) {
    let chart;
    let options = this.getChartOptions(raw);
    let data = new google.visualization.DataTable();
    let statuses = raw.statuses.map(function (state) {
      return [state.name, state.assessments];
    });
    this.options.chartOptions = options;
    this.options.data = data;

    data.addColumn('string', 'Status');
    data.addColumn('number', 'Count');
    data.addRows(statuses);

    chart = new google.visualization.PieChart(
      document.getElementById(elementId));
    this.options.chart = chart;

    google.visualization.events.addListener(chart, 'select', () => {
      let selectedItem = chart.getSelection()[0];
      if (selectedItem) {
        let topping = data.getValue(selectedItem.row, 0);
        router.attr({
          widget: 'assessment_widget',
          state: [topping],
        });
      }
    });

    chart.draw(data, options);
    setTimeout(function () {
      $(window).trigger('resize');
    }, 0);

    return chart;
  },
  prepareLegend: function (type, chart, data) {
    let legendData = [];
    let chartOptions = this.options.context.charts[type];
    let colorsMap = this.options.colorsMap;

    data.statuses.forEach(function (status, rowIndex) {
      legendData.push({
        title: status.name,
        count: status.assessments,
        percent: (status.assessments / data.total.assessments * 100).toFixed(1),
        evidence: status.evidence,
        rowIndex: rowIndex,
        color: colorsMap[status.name],
      });
    });

    chartOptions.attr('legend', legendData);

    this.element.find('#piechart_audit_assessments_chart-legend tbody')
      .off('mouseenter', 'tr')
      .on('mouseenter', 'tr', function () {
        let $el = $(this);
        let rowIndex = $el.data('row-index');

        if (_.isNumber(rowIndex)) {
          chart.setSelection([{row: rowIndex, column: null}]);
        }
      })
      .on('mouseleave', 'tr', function () {
        chart.setSelection(null);
      });
  },
  getChartOptions: function (raw) {
    let options = _.assign({}, this.options.chartOptions);
    let colorMaps = this.options.colorsMap;
    options.colors = raw.statuses.map(function (e) {
      return colorMaps[e.name];
    });

    return options;
  },
  '{window} resize': function (ev) {
    let chart = this.options.chart;
    let data = this.options.data;
    let options = this.options.chartOptions;
    let isSummaryWidgetShown = this.options.isShown;

    if (isSummaryWidgetShown && chart && options && data) {
      chart.draw(data, options);
    }
  },
  setState: function (type, data, isLoading) {
    let chartOptions = this.options.context.charts[type];
    chartOptions.attr('total', data.total.assessments);
    chartOptions.attr('totalEvidence', data.total.evidence);
    chartOptions.attr('any', data.total.assessments > 0);
    chartOptions.attr('none', isLoading || data.total.assessments === 0);
    chartOptions.attr('isLoading', isLoading);
    chartOptions.attr('isLoaded', !isLoading);
    if (isLoading) {
      chartOptions.attr('legend', []);
    }
  },
  parseStatuses: function (type, raw) {
    let statuses = getDefaultStatesForModel(type).map((status) => {
      return {
        name: status,
        assessments: 0,
        evidence: 0,
      };
    });

    raw.statuses.forEach((item) => {
      let statusName;
      let statusObj;

      if (item.name === 'Completed') {
        statusName = item.verified ?
          'Completed and Verified' : 'Completed (no verification)';
      } else {
        statusName = item.name;
      }

      statusObj = statuses.find((el) => {
        return el.name === statusName;
      });
      statusObj.assessments = item.assessments;
      statusObj.evidence = item.evidence;
    });

    return {
      statuses: statuses,
      total: raw.total,
    };
  },
  /**
   * Get count of Assessments and mapped evidence with breakdown by status
   * @param {Number} auditId
   * @return {Promise<Array>}
   * @example
   * Example of response:
   * {
   *  statuses: [
   *    {
   *      "name": "Not Started",
   *      "verified": 0,
   *      "assessments": X,
   *      "evidence": Y
   *    },
   *    {"name": "In Progress", ...},
   *    {"name": "In Review", ...},
   *    {
   *      "name": "Completed",
   *      "verified": 1,
   *      ...
   *    },
   *    {
   *      "name": "Completed",
   *      "verified": 0,
   *      ...
   *    },
   *    {"name": "Deprecated", ...},
   *    {"name": "Rework Needed", ...}
   *  ],
   *  total: {
   *    assessments: N,
   *    evidence: L
   *  }
   * }
   * X - number of assessments with this status;
   * Y - number of evidence attached to assessments with this status;
   * N, L - total count of assessments, evidence accordingly in this audit.
   */
  getStatuses: function (auditId) {
    return $.get('/api/audits/'+ auditId + '/summary');
  },
  loadChartLibrary: function (callback) {
    if (typeof google !== 'undefined' &&
        typeof google.charts !== 'undefined') {
      callback();
      return;
    }
    GGRC.Utils.loadScript('https://www.gstatic.com/charts/loader.js', function () {
      google.charts.load('45', {packages: ['corechart']});
      google.charts.setOnLoadCallback(callback);
    });
  },
});
