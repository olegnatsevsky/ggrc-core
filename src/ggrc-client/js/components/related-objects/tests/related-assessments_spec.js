/*
 Copyright (C) 2018 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

import Component from '../related-assessments';
import {getComponentVM} from '../../../../js_specs/spec_helpers';
import * as caUtils from '../../../plugins/utils/ca-utils';

describe('GGRC.Components.relatedAssessments', () => {
  describe('viewModel scope', () => {
    let originalModels;
    let viewModel;

    beforeEach(() => {
      viewModel = getComponentVM(Component);
    });

    describe('relatedObjectsTitle get() method', () => {
      beforeAll(() => {
        originalModels = CMS.Models;
      });

      afterAll(() => {
        CMS.Models = originalModels;
      });

      it('returns title based on instance.assessment_type', () => {
        let asmtModelType = 'Model1';
        let modelPlural = 'Awesome_models1';
        let expectedTitle;

        CMS.Models = {
          [asmtModelType]: {
            model_plural: modelPlural,
          },
        };
        viewModel.attr('instance.assessment_type', asmtModelType);
        expectedTitle = `Related ${modelPlural}`;

        expect(viewModel.attr('relatedObjectsTitle')).toBe(expectedTitle);
      });

      it(`returns title based on instance.type if is gotten related
          assessments not from assessment info pane`, () => {
        let modelType = 'Model1';
        let modelPlural = 'Awesome_models1';
        let expectedTitle;

        CMS.Models = {
          [modelType]: {
            model_plural: modelPlural,
          },
        };
        viewModel.attr('instance.assessment_type', null);
        viewModel.attr('instance.type', modelType);
        expectedTitle = `Related ${modelPlural}`;

        expect(viewModel.attr('relatedObjectsTitle')).toBe(expectedTitle);
      });
    });

    describe('loadRelatedAssessments() method', () => {
      const mockRelatedAsmtResponse = (response) => {
        spyOn(viewModel.attr('instance'), 'getRelatedAssessments')
          .and.returnValue(can.Deferred().resolve(response));
      };

      beforeEach(() => {
        spyOn(caUtils, 'prepareCustomAttributes');

        viewModel.attr('instance', {
          getRelatedAssessments() {},
        });
      });

      it('should not initialize the base array if response is empty',
        (done) => {
          mockRelatedAsmtResponse({
            total: 0,
            data: [],
          });

          viewModel.loadRelatedAssessments().then(() => {
            expect(viewModel.attr('paging.total')).toEqual(0);
            expect(viewModel.attr('relatedAssessments').length).toEqual(0);
            done();
          });
        });

      it('should initialize a base array', (done) => {
        mockRelatedAsmtResponse({
          total: 42,
          data: [{}, {}, {}, {}],
        });

        viewModel.loadRelatedAssessments().then(() => {
          let relAsmt = viewModel.attr('relatedAssessments');

          expect(viewModel.attr('paging.total')).toEqual(42);
          expect(relAsmt.length).toEqual(4);
          expect(relAsmt.filter((el) => el.instance).length).toEqual(4);
          done();
        });
      });

      it('should reset the loading flag after an error', (done) => {
        const relatedAssessments = viewModel.attr('relatedAssessments');

        spyOn(viewModel.attr('instance'), 'getRelatedAssessments')
          .and.returnValue(can.Deferred().reject());

        spyOn(relatedAssessments, 'replace');

        viewModel.loadRelatedAssessments().always(() => {
          expect(relatedAssessments.replace).not.toHaveBeenCalled();
          expect(caUtils.prepareCustomAttributes).not.toHaveBeenCalled();
          expect(viewModel.attr('loading')).toEqual(false);
          done();
        });
      });
    });

    describe('unableToReuse get() method', ()=> {
      it(`returns false if there are selected evidences 
        and it is not saving`, ()=> {
          viewModel.attr('isSaving', false);
          viewModel.attr('selectedEvidences', ['item']);

          let result = viewModel.attr('unableToReuse');

          expect(result).toBe(false);
        });

      describe('returns true', ()=> {
        it('if there are no selected items and it is not saving', ()=> {
          viewModel.attr('isSaving', false);
          viewModel.attr('selectedEvidences', []);

          let result = viewModel.attr('unableToReuse');

          expect(result).toBe(true);
        });

        it('if there are selected items and it is saving', ()=> {
          viewModel.attr('isSaving', true);
          viewModel.attr('selectedEvidences', ['item']);

          let result = viewModel.attr('unableToReuse');

          expect(result).toBe(true);
        });

        it('if there are no selected items and it is saving', ()=> {
          viewModel.attr('isSaving', true);
          viewModel.attr('selectedEvidences', []);

          let result = viewModel.attr('unableToReuse');

          expect(result).toBe(true);
        });
      });
    });

    describe('buildEvidenceModel() method', ()=> {
      beforeEach(()=> {
        viewModel.attr({
          instance: {
            context: {id: 'contextId'},
            id: 'instanceId',
            type: 'instanceType',
          },
        });
      });

      it('builds EVIDENCE model correctly', ()=> {
        let evidence = new can.Map({
          kind: 'EVIDENCE',
          title: 'title',
          gdrive_id: 'gdrive_id',
        });

        let result = viewModel.buildEvidenceModel(evidence);

        expect(result.serialize()).toEqual({
          context: {
            id: 'contextId',
            type: 'Context',
          },
          parent_obj: {
            id: 'instanceId',
            type: 'instanceType',
          },
          kind: 'EVIDENCE',
          title: 'title',
          source_gdrive_id: 'gdrive_id',
        });
      });

      it('builds URL model correctly', ()=> {
        let evidence = new can.Map({
          kind: 'URL',
          title: 'title',
          link: 'link',
        });

        let result = viewModel.buildEvidenceModel(evidence);

        expect(result.serialize()).toEqual({
          context: {
            id: 'contextId',
            type: 'Context',
          },
          parent_obj: {
            id: 'instanceId',
            type: 'instanceType',
          },
          kind: 'URL',
          title: 'title',
          link: 'link',
        });
      });
    });

    describe('reuseSelected() method', ()=> {
      let saveDfd;
      let saveSpy;
      beforeEach(()=> {
        viewModel.attr('selectedEvidences', [{
          id: 'id',
          title: 'evidence1',
        }]);

        saveDfd = can.Deferred();
        saveSpy = jasmine.createSpy().and.returnValue(saveDfd);
        spyOn(viewModel, 'buildEvidenceModel').and.returnValue({
          save: saveSpy,
        });
      });

      it('turning on "isSaving" flag', ()=> {
        viewModel.attr('isSaving', false);

        viewModel.reuseSelected();

        expect(viewModel.attr('isSaving')).toBe(true);
      });

      it('builds evidence model', ()=> {
        viewModel.reuseSelected();

        expect(viewModel.buildEvidenceModel).toHaveBeenCalled();
      });

      it('saves builded model', ()=> {
        viewModel.reuseSelected();

        expect(saveSpy).toHaveBeenCalled();
      });

      describe('after saving', ()=> {
        it('cleans selectedEvidences', (done)=> {
          viewModel.reuseSelected();

          saveDfd.resolve().then(()=> {
            expect(viewModel.attr('selectedEvidences.length')).toBe(0);
            done();
          });
        });

        it('turns off isSaving flag', (done)=> {
          viewModel.reuseSelected();

          viewModel.attr('isSaving', true);

          saveDfd.resolve().then(()=> {
            expect(viewModel.attr('isSaving')).toBe(false);
            done();
          });
        });

        it('dispatches "afterObjectReused" event', (done)=> {
          spyOn(viewModel, 'dispatch');

          viewModel.reuseSelected();

          saveDfd.resolve().then(()=> {
            expect(viewModel.dispatch)
              .toHaveBeenCalledWith('afterObjectReused');
            done();
          });
        });

        it('dispatches "refreshInstance" event on instance', (done)=> {
          spyOn(viewModel.attr('instance'), 'dispatch');

          viewModel.reuseSelected();

          saveDfd.resolve().then(()=> {
            expect(viewModel.attr('instance').dispatch)
              .toHaveBeenCalledWith('refreshInstance');
            done();
          });
        });
      });
    });

    describe('checkReuseAbility() method', ()=> {
      it('returns true if evidence is not a file', ()=> {
        let evidence = new can.Map({
          kind: 'URL',
        });

        let result = viewModel.checkReuseAbility(evidence);

        expect(result).toBe(true);
      });

      it('returns true if evidence is a file with gdrive_id', ()=> {
        let evidence = new can.Map({
          kind: 'EVIDENCE',
          gdrive_id: 'gdrive_id',
        });

        let result = viewModel.checkReuseAbility(evidence);

        expect(result).toBe(true);
      });

      it('returns false if evidence is a file without gdrive_id', ()=> {
        let evidence = new can.Map({
          kind: 'EVIDENCE',
          gdrive_id: '',
        });

        let result = viewModel.checkReuseAbility(evidence);

        expect(result).toBe(false);
      });
    });
  });

  describe('helpers', ()=> {
    let viewModel;
    beforeEach(()=> {
      viewModel = getComponentVM(Component);
    });

    describe('isAllowedToReuse helper', ()=> {
      let isAllowedToReuse;
      let evidence;
      beforeEach(()=> {
        isAllowedToReuse = Component.prototype.helpers
          .isAllowedToReuse.bind(viewModel);
        spyOn(viewModel, 'checkReuseAbility');
        evidence = jasmine.createSpy();
      });

      it('calls checkReuseAbility()', ()=>{
        isAllowedToReuse(evidence);

        expect(viewModel.checkReuseAbility).toHaveBeenCalled();
      });

      it('returns checkReuseAbility result', ()=> {
        let abilityResult = {test: true};
        viewModel.checkReuseAbility.and.returnValue(abilityResult);

        let result = isAllowedToReuse(evidence);

        expect(result).toBe(abilityResult);
      });

      it('resolves compute argument', ()=> {
        isAllowedToReuse(evidence);

        expect(evidence).toHaveBeenCalled();
      });
    });

    describe('ifAllowedToReuse helper', ()=> {
      let ifAllowedToReuse;
      let evidence;
      let options;
      beforeEach(()=> {
        ifAllowedToReuse = Component.prototype.helpers
          .ifAllowedToReuse.bind(viewModel);
        spyOn(viewModel, 'checkReuseAbility');
        evidence = {test: true};
        options = {
          fn: jasmine.createSpy(),
          inverse: jasmine.createSpy(),
        };
        spyOn(Mustache, 'resolve');
      });

      it('resolves compute argument', ()=> {
        ifAllowedToReuse(evidence, options);

        expect(Mustache.resolve).toHaveBeenCalledWith(evidence);
      });

      it('calls fn if able to reuse', ()=> {
        viewModel.checkReuseAbility.and.returnValue(true);

        ifAllowedToReuse(evidence, options);

        expect(options.fn).toHaveBeenCalled();
      });

      it('calls inverse if not able to reuse', ()=> {
        viewModel.checkReuseAbility.and.returnValue(false);

        ifAllowedToReuse(evidence, options);

        expect(options.inverse).toHaveBeenCalled();
      });
    });
  });
});
