/*
    Copyright (C) 2018 Google Inc.
    Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

(function (GGRC, CMS, can) {
  'use strict';

  GGRC.Components('createUrl', {
    tag: 'create-url',
    viewModel: {
      value: null,
      context: null,
      create: function () {
        let value = this.attr('value');
        let self = this;
        let document;
        let attrs;

        if (!value || !value.length) {
          GGRC.Errors.notifier('error', 'Please enter a URL.');
          return;
        }

        attrs = {
          link: value,
          title: value,
          context: this.attr('context') || new CMS.Models.Context({id: null}),
          kind: 'URL',
          created_at: new Date(),
          isDraft: true,
          _stamp: Date.now(),
        };

        document = new CMS.Models.Document(attrs);
        this.dispatch({type: 'beforeCreate', items: [document]});
        document.save()
          .fail(function () {
            GGRC.Errors.notifier('error', 'Unable to create URL.');
          })
          .done(function (data) {
            self.dispatch({type: 'created', item: data});
            self.clear();
          });
      },
      clear: function () {
        this.attr('value', null);
      },
    },
  });
})(window.GGRC, window.CMS, window.can);
