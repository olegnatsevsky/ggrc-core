/*
    Copyright (C) 2018 Google Inc.
    Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import {
  buildParam,
  batchRequests,
} from '../../plugins/utils/query-api-utils';
import {initCounts} from '../../plugins/utils/current-page-utils';

(function (can, $, _, GGRC) {
  'use strict';

  let DOCUMENT_KIND_MAP = {};

  DOCUMENT_KIND_MAP[CMS.Models.Document.FILE] = 'documents_file';
  DOCUMENT_KIND_MAP[CMS.Models.Document.URL] = 'documents_url';
  DOCUMENT_KIND_MAP[CMS.Models.Document.REFERENCE_URL] = 'documents_reference_url';

  GGRC.Components('relatedDocuments', {
    tag: 'related-documents',
    viewModel: {
      instance: {},
      modelType: 'Document',
      kind: '@',
      documents: [],
      isLoading: false,
      pendingItemsChanged: false,
      define: {

        // automatically refresh instance on related document create/remove
        autorefresh: {
          type: 'boolean',
          value: true,
        },
        customLoader: {
          type: 'boolean',
          value: false,
        },
      },
      getDocumentsQuery: function () {
        let relevantFilters = [{
          type: this.attr('instance.type'),
          id: this.attr('instance.id'),
          operation: 'relevant',
        }];
        let additionalFilter = this.attr('kind') ?
        {
          expression: {
            left: 'kind',
            op: {name: '='},
            right: this.attr('kind'),
          },
        } :
        [];

        let modelType = this.attr('modelType');
        let query =
          buildParam(modelType, {}, relevantFilters, [], additionalFilter);
        query.order_by = [{name: 'created_at', desc: true}];

        return query;
      },
      loadDocuments: function () {
        const query = this.getDocumentsQuery();

        this.attr('isLoading', true);
        this.refreshTabCounts();

        let modelType = this.attr('modelType');
        return batchRequests(query).then((response) => {
          const documents = response[modelType].values;
          this.attr('documents').replace(documents);
          this.attr('isLoading', false);
        });
      },
      setDocuments: function () {
        let instance;
        let kind;
        let documentPath;
        let documents;

        // don't load documents if they are comes from outside
        if (this.attr('customLoader')) {
          return;
        }
        // load documents for non-snapshots objects
        if (!this.attr('isSnapshot')) {
          this.loadDocuments();
          return;
        }

        instance = this.attr('instance');
        kind = this.attr('kind');

        if (kind) {
          documentPath = DOCUMENT_KIND_MAP[kind];
          documents = instance[documentPath];
        } else {
          // We need to display URL and Evidences together ("Related
          // Assessments pane")
          documents = instance.document_url.concat(instance.document_evidence);
        }

        this.attr('documents').replace(documents);
      },
      removeDocument: function (event) {
        let item = event.item;
        let index = this.attr('documents').indexOf(item);
        this.attr('isLoading', true);
        return this.attr('documents').splice(index, 1);
      },
      addDocuments: function (event) {
        let items = event.items;
        this.attr('isLoading', true);
        return this.attr('documents').unshift
          .apply(this.attr('documents'), items);
      },
      createDocument: function (data) {
        let date = new Date();
        let modelType = this.attr('modelType');
        let document = new CMS.Models[modelType]({
          link: data,
          title: data,
          created_at: date.toISOString(),
          context: this.instance.context || new CMS.Models.Context({
            id: null,
          }),
          kind: this.kind,
        });
        return document;
      },
      saveDocument: function (document) {
        return document.save();
      },
      createRelationship: function (document) {
        let relationship = new CMS.Models.Relationship({
          source: this.instance,
          destination: document,
          context: this.instance.context ||
            new CMS.Models.Context({id: null}),
        });
        return relationship.save();
      },
      createRelatedDocument: function (data) {
        let self = this;
        let document = this.createDocument(data);

        this.attr('documents').unshift(document);
        this.attr('isLoading', true);

        return this.saveDocument(document)
          .then(this.createRelationship.bind(this))
          .then(function (result) {
            self.fetchAndUpdate(self.instance);
            self.refreshRelatedDocuments();
          })
          .fail(function (err) {
            console.error('Unable to create related document: ', err);
          })
          .done(function () {
            self.attr('isLoading', false);
          });
      },
      removeRelationship: function (relationship) {
        return relationship.refresh()
          .then(function (refreshedRelationship) {
            return refreshedRelationship.destroy();
          });
      },
      removeRelatedDocument: async function (document) {
        let self = this;
        let documents;
        let relationship = await CMS.Models.Relationship.findRelationship(
          document, this.instance);
        if (!relationship.id) {
          console.log('Unable to find relationship');
          return can.Deferred().reject({
            error: 'Unable to find relationship',
          });
        }

        documents = this.attr('documents').filter(function (item) {
          return item.id !== document.id;
        });

        this.attr('isLoading', true);
        this.attr('documents', documents);

        return this.removeRelationship(relationship)
          .then(function () {
            self.fetchAndUpdate(self.instance);
            self.refreshRelatedDocuments();
          })
          .fail(function (err) {
            console.error('Unable to remove related document: ', err);
          })
          .done(function () {
            self.attr('isLoading', false);
          });
      },
      markDocumentForDeletion: function (document) {
        let documents = this.attr('documents').filter(function (item) {
          return item !== document;
        });

        this.attr('documents', documents);
        this.instance.mark_for_deletion('related_objects_as_source', document);
        this.attr('pendingItemsChanged', true);
      },
      markDocumentForAddition: function (data) {
        let self = this;
        let document = this.createDocument(data);

        this.attr('documents').unshift(document);
        this.attr('isLoading', true);

        this.attr('pendingItemsChanged', true);
        return this.saveDocument(document).then(function () {
          self.instance.mark_for_addition(
            'related_objects_as_source',
            document
          );
          self.attr('isLoading', false);
        });
      },
      fetchAndUpdate: function (instance) {
        instance.refresh().then(function (refreshed) {
          refreshed.save();
        });
      },
      refreshRelatedDocuments: function () {
        if (this.autorefresh) {
          this.loadDocuments();
        }
      },
      refreshTabCounts: function () {
        let pageInstance = GGRC.page_instance();
        let modelType = this.attr('modelType');
        initCounts(
          [modelType],
          pageInstance.type,
          pageInstance.id
        );
      },
    },
    init: function () {
      let instance = this.viewModel.attr('instance');
      let isNew = instance.isNew();
      let isSnapshot = !!(instance.snapshot || instance.isRevision);

      // don't need to load documents for unsaved instance
      if (!isNew) {
        this.viewModel.attr('isSnapshot', isSnapshot);
        this.viewModel.setDocuments();
      }
    },
    events: {
      '{viewModel.instance} resolvePendingBindings': function () {
        this.viewModel.refreshRelatedDocuments();
      },
    },
  });
})(window.can, window.can.$, window._, window.GGRC);
