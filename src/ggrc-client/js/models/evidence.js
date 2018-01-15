/*
  Copyright (C) 2017 Google Inc.
  Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/
import {getRole} from '../plugins/utils/acl-utils';

const getAccessControlList = ()=> {
  let adminRole = getRole('Evidence', 'Admin');

  return adminRole ? [{
    ac_role_id: adminRole.id,
    person: {type: 'Person', id: GGRC.current_user.id},
  }] : [];
};

can.Model.Cacheable('CMS.Models.Evidence', {
  root_object: 'evidence',
  root_collection: 'evidence',
  title_singular: 'Evidence',
  title_plural: 'Evidence',
  category: 'governance',
  findAll: 'GET /api/evidence',
  findOne: 'GET /api/evidence/{id}',
  create: 'POST /api/evidence',
  update: 'PUT /api/evidence/{id}',
  destroy: 'DELETE /api/evidence/{id}',
  mixins: [
    'accessControlList',
    'ca_update',
  ],
  attributes: {
    context: 'CMS.Models.Context.stub',
  },
  isRoleable: true,
  statuses: [
    'Active',
    'Deprecated',
  ],
  kinds: [
    {title: 'File', value: 'FILE'},
    {title: 'URL', value: 'URL'},
  ],
  defaults: {
    access_control_list: getAccessControlList(),
    kind: 'FILE',
    status: 'Active',
  },
  tree_view_options: {
    attr_view: GGRC.mustache_path + '/evidence/tree-item-attr.mustache',
    display_attr_names: [
      'title',
      'status',
      'updated_at',
    ],
    attr_list: [
      {attr_title: 'Title', attr_name: 'title'},
      {attr_title: 'State', attr_name: 'status'},
      {attr_title: 'Type', attr_name: 'kind'},
      {attr_title: 'Last Updated By', attr_name: 'modified_by'},
      {attr_title: 'Last Updated', attr_name: 'updated_at'},
      {attr_title: 'Last Deprecated Date', attr_name: 'end_date'},
      {attr_title: 'Archived', attr_name: 'archived'},
    ],
  },
  init() {
    this.validateNonBlank('title');
    this._super(...arguments);
  },
}, {
  kindTitle() {
    let value = this.attr('kind');
    let title = _.findWhere(this.class.kinds, {value}).title;
    return title;
  },
});
