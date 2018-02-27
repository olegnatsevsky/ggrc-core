/*
 Copyright (C) 2018 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

import * as CurrentPageUtils from '../../../plugins/utils/current-page-utils';
import BaseTreeItemVM from '../tree-item-base-vm';

describe('GGRC.VM.BaseTreeItemVM', function () {
  'use strict';

  let vm;

  beforeEach(function () {
    vm = new BaseTreeItemVM();
  });

  describe('onExpand() method', function () {
    it('converts expanded property to the opposite value', function () {
      vm.attr('expanded', true);

      vm.onExpand();

      expect(vm.attr('expanded')).toBeFalsy();
    });

    it('converts expanded property to the opposite value', function () {
      vm.attr('expanded', false);

      vm.onExpand();

      expect(vm.attr('expanded')).toBeTruthy();
    });
  });

  describe('onClick() method', function () {
    let event;
    beforeEach(function () {
      spyOn(vm, 'select');
      event = {};
    });

    describe('if event target is link', ()=> {
      beforeEach(()=> {
        event = {
          target: $('<a class="link"></a>'),
          stopPropagation: jasmine.createSpy(),
        };
      });

      it('it is stopping event propagation', ()=> {
        vm.onClick('element', event);

        expect(event.stopPropagation).toHaveBeenCalled();
      });

      it('does not select current item', ()=> {
        vm.onClick('element', event);

        expect(vm.select).not.toHaveBeenCalled();
      });
    });

    describe('if instance is Cycle', ()=> {
      beforeEach(()=> {
        vm.attr('instance', new can.Map({
          type: 'Cycle',
        }));
      });

      describe('toggle "expanded" option if page is "Workflow"', ()=> {
        beforeEach(()=> {
          spyOn(CurrentPageUtils, 'getPageType')
            .and.returnValue('Workflow');
        });
        it('when option was false', ()=> {
          vm.attr('expanded', false);

          vm.onClick('element', event);

          expect(vm.attr('expanded')).toBe(true);
        });

        it('when option was true', ()=> {
          vm.attr('expanded', true);

          vm.onClick('element', event);

          expect(vm.attr('expanded')).toBe(false);
        });
      });

      it('call select() if page is not Workflow', ()=> {
        spyOn(CurrentPageUtils, 'getPageType')
          .and.returnValue('AnotherType');
        vm.attr('result', true);

        vm.onClick('element', event);

        expect(vm.select).toHaveBeenCalledWith('element');
      });
    });

    describe('if instance is CycleTaskGroup', ()=> {
      beforeEach(()=> {
        vm.attr('instance', new can.Map({
          type: 'CycleTaskGroup',
        }));
      });

      describe('toggle "expanded" option if page is "Workflow"', ()=> {
        beforeEach(()=> {
          spyOn(CurrentPageUtils, 'getPageType')
            .and.returnValue('Workflow');
        });

        it('when option was false', ()=> {
          vm.attr('expanded', false);

          vm.onClick('element', event);

          expect(vm.attr('expanded')).toBe(true);
        });

        it('when option was true', ()=> {
          vm.attr('expanded', true);

          vm.onClick('element', event);

          expect(vm.attr('expanded')).toBe(false);
        });
      });

      it('call select() if page is not Workflow', ()=> {
        spyOn(CurrentPageUtils, 'getPageType')
          .and.returnValue('AnotherType');
        vm.attr('result', true);

        vm.onClick('element', event);

        expect(vm.select).toHaveBeenCalledWith('element');
      });
    });
  });

  describe('select() method', ()=> {
    let fakeElement;

    beforeEach(()=> {
      fakeElement = {
        closest: jasmine.createSpy().and.returnValue('closest'),
      };
      spyOn(can, 'trigger');
      vm.attr('instance', 'fakeInstance');
      vm.attr('itemSelector', 'fakeSelector');
    });

    it('looks for correct element', ()=> {
      vm.select(fakeElement);

      expect(fakeElement.closest).toHaveBeenCalledWith('fakeSelector');
    });

    it('triggers "selectTreeItem" event', ()=> {
      vm.select(fakeElement);

      expect(can.trigger).toHaveBeenCalledWith(
        'closest',
        'selectTreeItem',
        ['closest', 'fakeInstance']);
    });
  });
});
