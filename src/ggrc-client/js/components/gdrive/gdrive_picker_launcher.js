/*
 * Copyright (C) 2018 Google Inc.
 * Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

import {
  uploadFiles,
  findGDriveItemById,
  GDRIVE_PICKER_ERR_CANCEL,
} from '../../plugins/utils/gdrive-picker-utils.js';
import {backendGdriveClient} from '../../plugins/ggrc-gapi-client';

(function (can, $, GGRC, CMS) {
  'use strict';

  GGRC.Components('gDrivePickerLauncher', {
    tag: 'ggrc-gdrive-picker-launcher',
    template: can.view(GGRC.mustache_path + '/gdrive/gdrive_file.mustache'),
    viewModel: {
      define: {
        isInactive: {
          get: function () {
            return this.attr('disabled');
          },
        },
      },
      modelType: 'Document',
      tooltip: null,
      instance: {},
      link_class: '@',
      click_event: '@',
      confirmationCallback: '@',
      pickerActive: false,
      disabled: false,
      isUploading: false,

      beforeCreateHandler: function (files) {
        let tempFiles = files.map(function (file) {
          return {
            title: file.title,
            link: file.url,
            created_at: new Date(),
            isDraft: true,
          };
        });
        this.dispatch({
          type: 'onBeforeAttach',
          items: tempFiles,
        });
      },
      onKeyup(element, event) {
        const ESCAPE_KEY_CODE = 27;
        const escapeKeyWasPressed = event.keyCode === ESCAPE_KEY_CODE;

        if (escapeKeyWasPressed) {
          const $element = $(element);
          event.stopPropagation();
          // unset focus for attach button
          $element.blur();
        }
      },
      onClickHandler: function (scope, el, event) {
        let eventType = this.attr('click_event');
        let handler = this[eventType] || function () {};
        let confirmation = can.isFunction(this.confirmationCallback) ?
          this.confirmationCallback() :
          null;
        let args = arguments;
        let that = this;

        event.preventDefault();
        can.when(confirmation).then(function () {
          handler.apply(that, args);
        });
      },
      trigger_upload: function (scope, el) {
        // upload files without a parent folder (risk assesment)

        this.attr('isUploading', true);
        uploadFiles({
          parentId: el.data('folder-id'),
          pickFolder: el.data('type') === 'folders',
        }).then((files) => {
          scope.attr('pickerActive', false);
          this.beforeCreateHandler(files);

          this.createDocumentModel(files)
            .then((docs) => {
              el.trigger('modal:success', {arr: docs});
            })
            .always(() => {
              this.attr('isUploading', false);
              this.dispatch('finish');
            });
        }).fail((err)=>{
          if ( err && err.type === GDRIVE_PICKER_ERR_CANCEL ) {
            el.trigger('rejected');
          }
          this.attr('isUploading', false);
        });
      },

      trigger_upload_parent: function (scope, el) {
        // upload files with a parent folder (audits and workflows)
        let that = this;
        let parentFolderDfd;
        let folderId;

        if (that.instance.attr('_transient.folder')) {
          parentFolderDfd = can.when(
            [{instance: this.instance.attr('_transient.folder')}]
          );
        } else {
          folderId = this.instance.attr('folder');

          parentFolderDfd = findGDriveItemById(folderId);
        }
        can.Control.prototype.bindXHRToButton(parentFolderDfd, el);

        parentFolderDfd
          .done(function (parentFolder) {
            that.attr('isUploading', true);
            uploadFiles({
              parentId: parentFolder.id,
            })
              .then(function (files) {
                that.beforeCreateHandler(files);

                that.createDocumentModel(files)
                  .then((docs)=> {
                    el.trigger('modal:success', {arr: docs});
                  })
                  .always(()=> {
                    that.attr('isUploading', false);
                    that.dispatch('finish');
                  });
              })
              .fail(function () {
                // This case happens when user have no access to write in audit folder
                let error = _.last(arguments);
                if (error && error.code === 403) {
                  GGRC.Errors.notifier('error', GGRC.Errors.messages[403]);
                  el.trigger('modal:success');
                } else if ( error && error.type !== GDRIVE_PICKER_ERR_CANCEL ) {
                  GGRC.Errors.notifier('error', error && error.message);
                }
                that.dispatch('finish');
                that.attr('isUploading', false);
              });
          })
          .fail(function () {
            el.trigger('ajax:flash', {
              warning: 'Can\'t upload: No GDrive folder found',
            });
          });
      },

      createDocumentModel: function (files) {
        let instanceId = this.attr('instance.id');
        let instanceType = this.attr('instance.type');
        let contextId = this.attr('instance.context.id') || null;
        let modelType = this.attr('modelType');
        let ModelClass = CMS.Models[modelType];

        let dfdDocs = files.map(function (file) {
          let model = new ModelClass({
            context: {id: contextId},
            title: file.title,
            source_gdrive_id: file.id,
            is_uploaded: file.newUpload,
            parent_obj: {
              id: instanceId,
              type: instanceType,
            },
          });

          return backendGdriveClient.withAuth(()=> {
            return model.save();
          });
        });
        // waiting for all docs promises
        return can.when(...dfdDocs).then(()=> {
          this.attr('instance').refresh();
          return can.makeArray(arguments);
        }, (xhr)=> {
          let message = (xhr.responseJSON && xhr.responseJSON.message) ?
            xhr.responseJSON.message :
            xhr.responseText;

          if (message) {
            GGRC.Errors.notifier('error', message);
          }
        });
      },
    },
  });
})(window.can, window.can.$, window.GGRC, window.CMS);
