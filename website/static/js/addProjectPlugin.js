/**
 * UI and function to add project
 */
'use strict';

require('css/add-project-plugin.css');
var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');

// XHR configuration to get apiserver connection to work
var xhrconfig = function (xhr) {
    xhr.withCredentials = true;
};


var AddProject = {
    controller : function (options) {
        var self = this;
        self.defaults = {
            buttonTemplate : m('.btn.btn-primary[data-toggle="modal"][data-target="#addProjectModal"]', 'Add new project'),
            parentID : null,
            modalID : 'addProjectModal',
            stayCallback :null, // Function to call when user decides to stay after project creation
            categoryList : []
        };
        self.viewState = m.prop('form'); // 'processing', 'success', 'error';
        self.options = $.extend({}, self.defaults, options);
        self.showMore = m.prop(false);
        self.newProjectName = m.prop('');
        self.newProjectDesc = m.prop('');
        self.newProjectCategory = m.prop('project');
        self.goToProjectLink = m.prop('');
        self.saveResult = m.prop({});
        self.errorMessageType = m.prop('unknown');
        self.errorMessage = {
            'unknown' : 'There was an unknown error. Please try again later.'
        };

        // Validation
        self.isValid = m.prop(false);
        self.checkValid = function _checkValid() {
            self.isValid(self.newProjectName().trim().length > 0);
        };
        self.add = function _add () {
            var url;
            var data;
            self.viewState('processing');
            if(self.options.parentID) {
                url = $osf.apiV2Url('nodes/' + self.options.parentID + '/children/', { query : {}});
            } else {
                url = $osf.apiV2Url('nodes/', { query : {}});
            }
            data = {
                    'data' : {
                        'type': 'nodes',
                        'attributes': {
                            'title': self.newProjectName(),
                            'category': self.newProjectCategory(),
                            'description' : self.newProjectDesc()
                        }
                    }
                };
            var success = function _success (result) {
                self.viewState('success');
                self.goToProjectLink(result.data.links.html);
                self.saveResult(result);
            };
            var error = function _error (result) {
                self.viewState('error');
            };
            m.request({method : 'POST', url : url, data : data, config : xhrconfig})
                .then(success, error);
            self.newProjectName('');
        };
        self.reset = function _reset(){
            self.newProjectName('');
            self.viewState('form');
            self.newProjectDesc('');
            self.newProjectCategory('project');
            $('.modal').modal('hide');
        };
    },
    view : function (ctrl, options) {
        var templates = {
            form : m('.modal-content', [
                m('.modal-header', [
                    m('button.close[data-dismiss="modal"][aria-label="Close"]',{ onclick : function() {
                        ctrl.reset();
                        $osf.trackClick('dashboard', 'add-project', 'click-close-add-project-modal');
                    }}, [
                        m('span[aria-hidden="true"]','×')
                    ]),
                    m('h3.modal-title', 'Add new project')
                ]),
                m('.modal-body', [
                    m('.text-left', [
                        m('.form-group.m-v-sm', [
                            m('label[for="projectName].f-w-lg.text-bigger', 'Project Name'),
                            m('input[type="text"].form-control', {
                                onkeyup: function(ev){
                                    if (ev.which === 13) {
                                         ctrl.add();
                                    }
                                    ctrl.newProjectName($(this).val());
                                    ctrl.checkValid();
                                },
                                onchange: function() {
                                    $osf.trackClick('dashboard', 'add-project', 'type-project-name');
                                },
                                value : ctrl.newProjectName()
                            })
                        ]),
                        m('.text-muted.pointer', { onclick : function(){
                            ctrl.showMore(!ctrl.showMore());
                            $osf.trackClick('dashboard', 'add-project', 'show-more-or-less');
                        }},[
                            ctrl.showMore() ? m('i.fa.fa-caret-down', { style: 'width: 10px;'}) : m('i.fa.fa-caret-right', { style: 'width: 10px;'}),
                            ' More (description, type)'
                        ]),
                        ctrl.showMore() ? [
                            m('.form-group.m-v-sm', [
                                m('label[for="projectDesc].f-w-lg.text-bigger', 'Project Description'),
                                m('textarea.form-control.noresize', {
                                    onchange: function() {
                                        m.withAttr('value', ctrl.newProjectDesc);
                                        $osf.trackClick('dashboard', 'add-project', 'type-project-description');
                                    },
                                    value : ctrl.newProjectDesc()
                                })
                            ]),
                            m('.f-w-lg.text-bigger','Category'),
                            m('.category-radio.p-h-md', [
                                ctrl.options.categoryList.map(function(cat){
                                    return m('.radio', m('label', [  m('input', {
                                        type: 'radio',
                                        name: 'projectCategory',
                                        value: cat.value,
                                        checked: ctrl.newProjectCategory() === cat.value,
                                        onchange : function() {
                                            m.withAttr('value', ctrl.newProjectCategory);
                                            $osf.trackClick('dashboard', 'add-project', 'select-project-category');
                                        }
                                    }), cat.display_name || m('i.text-muted', '(Empty category)') ]));

                                })
                            ])
                        ] : ''
                    ])
                ]),
                m('.modal-footer', [
                    m('button[type="button"].btn.btn-default[data-dismiss="modal"]', { onclick : function() {
                        ctrl.reset();
                        $osf.trackClick('dashboard', 'add-project', 'click-cancel-button');
                    }},  'Cancel'),
                    ctrl.isValid() ? m('button[type="button"].btn.btn-success', { onclick : function() {
                        ctrl.add();
                        $osf.trackClick('dashboard', 'add-project', 'click-add-button');
                    }},'Add') : m('button[type="button"].btn.btn-success[disabled]','Add')
                ])
            ]),
            processing : m('.modal-content',
                m('.modal-content',
                    m('.modal-header', [
                        m('button.close[data-dismiss="modal"][aria-label="Close"]',{ onclick : ctrl.reset}, [
                            m('span[aria-hidden="true"]','×')
                        ])
                    ]),
                    m('.modal-body.text-left', [
                            m('.add-project-processing', 'Saving your project...')
                        ]
                    )
                )
            ),
            success : m('.modal-content', [
                m('.modal-content',
                    m('.modal-body.text-left', [
                            m('button.close[data-dismiss="modal"][aria-label="Close"]',{ onclick : function() {
                                ctrl.reset();
                                $osf.trackClick('dashboard', 'add-project', 'click-close-success-modal');
                            }}, [
                                m('span[aria-hidden="true"]','×')
                            ]),
                            m('h4.add-project-success.text-success', 'Project created successfully!')
                        ]
                    ),
                    m('.modal-footer', [
                        m('button[type="button"].btn.btn-default[data-dismiss="modal"]', {
                            onclick : function() {
                                ctrl.reset();
                                ctrl.options.stayCallback.call(ctrl); // results are at ctrl.saveResult
                                $osf.trackClick('dashboard', 'add-project', 'keep-working-here');
                            }
                        },  'Keep working here'),
                        m('a.btn.btn-success', { href : ctrl.goToProjectLink(), onclick: function() {
                             $osf.trackClick('dashboard', 'add-project', 'go-to-new-project');
                        }},'Go to new project')
                    ])
                )
            ]),
            error : m('.modal-content', [
                m('.modal-content',
                    m('.modal-body.text-left', [
                            m('button.close[data-dismiss="modal"][aria-label="Close"]',{ onclick : function() {
                                ctrl.reset();
                                $osf.trackClick('dashboard', 'add-project', 'close-couldn\'t-create-your-project');
                                }}, [
                                m('span[aria-hidden="true"]','×')
                            ]),
                            m('h4.add-project-error.text-danger', 'Couldn\'t create your project'),
                            m('p', ctrl.errorMessage[ctrl.errorMessageType()])
                        ]
                    ),
                    m('.modal-footer', [
                        m('button[type="button"].btn.btn-default[data-dismiss="modal"]', {onclick: function() {
                            $osf.trackClick('dashboard', 'add-project', 'click-OK-couldn\'t-create-your-project');
                        }},  'OK')
                    ])
                )
            ])
        };

        return  m('span', [
            ctrl.options.buttonTemplate,
            m('#' + ctrl.options.modalID + '.modal.fade[tabindex=-1][role="dialog"][aria-labelledby="addProject"][aria-hidden="true"]',
                m('.modal-dialog.text-left',
                    templates[ctrl.viewState()]
                )
            )
        ]);
    }
};

module.exports = AddProject;