/**
 * Builds full page project browser
 */
'use strict';

var $ = require('jquery');  // jQuery
var m = require('mithril'); // exposes mithril methods, useful for redraw etc.
var ProjectOrganizer = require('js/project-organizer');
var $osf = require('js/osfHelpers');
var LogText = require('js/logTextParser');
var AddProject = require('js/addProjectPlugin');

if (!window.fileBrowserCounter) {
    window.fileBrowserCounter = 0;
}
function getUID() {
    window.fileBrowserCounter = window.fileBrowserCounter + 1;
    return window.fileBrowserCounter;
}

var xhrconfig = function (xhr) {
    xhr.withCredentials = true;
    xhr.setRequestHeader('Content-Type', 'application/vnd.api+json');
    xhr.setRequestHeader('Accept', 'application/vnd.api+json; ext=bulk');
};

// Refactor the information needed for filtering rows
function _formatDataforPO(item) {
    item.uid = item.id;
    item.name = item.attributes.title;
    item.tags = item.attributes.tags.toString();
    item.contributors = '';
    if (!item.embeds.contributors.data){
        console.log(item.embed.contributors.errors);
    } else {
        item.embeds.contributors.data.forEach(function(c){
            item.contributors += c.embeds.users.data.attributes.full_name;
        });
    }
    item.date = new $osf.FormattableDate(item.attributes.date_modified);
    return item;
}

var LinkObject = function (type, data, label, index) {
    if (type === undefined || data === undefined || label === undefined) {
        throw new Error('LinkObject expects type, data and label to be defined.');
    }
    if (index !== undefined && ( typeof index !== 'number' || index <= 0)){
        throw new Error('Index needs to be a number starting from 0; instead "' + index + '" was given.');
    }
    var self = this;
    self.id = getUID();
    self.type = type;
    self.data = data;
    self.label = label;
    self.index = index;  // For breadcrumbs to cut off when clicking parent level
    self.generateLink = function () {
        if (self.type === 'collection'){
                return $osf.apiV2Url(self.data.path, {
                        query : self.data.query
                    }
                );
        }
        else if (self.type === 'tag') {
            return $osf.apiV2Url('nodes/', { query : {'filter[tags]' : self.data.tag , 'related_counts' : true, 'embed' : 'contributors'}});
        }
        else if (self.type === 'name') {
            return $osf.apiV2Url('users/' + self.data.id + '/nodes/', { query : {'related_counts' : true, 'embed' : 'contributors' }});
        }
        else if (self.type === 'node') {
            return $osf.apiV2Url('nodes/' + self.data.uid + '/children/', { query : { 'related_counts' : true, 'embed' : 'contributors' }});
        }
        // If nothing
        throw new Error('Link could not be generated from linkObject data');
    };
    self.link = self.generateLink();
};


function _makeTree (flatData) {
    var root = {id:0, children: [], data : {} };
    var node_list = { 0 : root};
    var parentID;
    for (var i = 0; i < flatData.length; i++) {
        var n = _formatDataforPO(flatData[i]);
        if (!node_list[n.id]) { // If this node is not in the object list, add it
            node_list[n.id] = n;
            node_list[n.id].children = [];
        } else { // If this node is in object list it's likely because it was created as a parent so fill out the rest of the information
            n.children = node_list[n.id].children;
            node_list[n.id] = n;
        }

        if (n.relationships.parent){
            parentID = n.relationships.parent.links.related.href.split('/')[5]; // Find where parent id string can be extracted
        } else {
            parentID = null;
        }
        if(parentID && !n.attributes.registration ) {
            if(!node_list[parentID]){
                node_list[parentID] = { children : [] };
            }
            node_list[parentID].children.push(node_list[n.id]);

        } else {
            node_list[0].children.push(node_list[n.id]);
        }
    }
    console.log(root, node_list);
    return root.children;
}

/**
 * Returns the object to send to the API to end a node_link to collection
 * @param id {String} unique id of the node like 'ez8f3'
 * @returns {{data: {type: string, relationships: {nodes: {data: {type: string, id: *}}}}}}
 */
function buildCollectionNodeData (id) {
    return {
        'data' : {
            'type': 'node_links',
            'relationships': {
                'nodes': {
                    'data': {
                        'type': 'nodes',
                        'id': id
                    }
                }
            }
        }
    };
}

/**
 * Initialize File Browser. Prepeares an option object within FileBrowser
 * @constructor
 */
var FileBrowser = {
    controller : function (options) {
        var self = this;
        self.wrapperSelector = options.wrapperSelector;  // For encapsulating each implementation of this component in multiple use
        self.currentLink = ''; // Save the link to compare if a new link is being requested and avoid multiple calls
        self.reload = m.prop(false); // Gets set to true when treebeard link changes and it needs to be redrawn
        self.nonLoadTemplate = m.prop(m('.fb-non-load-template.m-md.p-md.osf-box', 'Loading...')); // Template for when data is not available or error happens

        // VIEW STATES
        self.showInfo = m.prop(true); // Show the info panel
        self.showSidebar = m.prop(true); // Show the links with collections etc. used in narrow views
        self.refreshView = m.prop(true); // Internal loading indicator
        self.allProjectsLoaded = m.prop(false);
        self.allProjects = m.prop([]);

        // Helper function to add properties for Treebeard to work properly
        self.addTbProperties = function(value){
            value.data.map(function (item) {
                item.kind = 'folder';
                item.uid = item.id;
                item.name = item.attributes.title;
                item.date = new $osf.FormattableDate(item.attributes.date_modified);
            });
            return value;
        };

        self.systemCollections = [
            new LinkObject('collection', { path : 'users/me/nodes/', query : { 'related_counts' : true, 'page[size]'  : 12, 'embed' : 'contributors' }, systemCollection : 'nodes'}, 'All My Projects'),
            new LinkObject('collection', { path : 'users/me/registrations/', query : { 'related_counts' : true, 'page[size]'  : 12, 'embed' : 'contributors'}, systemCollection : 'registrations'}, 'All My Registrations')
        ];
        // Initial Breadcrumb for All my projects
        self.breadcrumbs = m.prop([
            new LinkObject('collection', { path : 'users/me/nodes/', query : { 'related_counts' : true, 'embed' : 'contributors' }, systemCollection : 'nodes'}, 'All My Projects')
        ]);
        // Calculate name filters
        self.nameFilters = [];
        // Calculate tag filters
        self.tagFilters = [];

        // Placeholder for node data
        self.data = m.prop([]);

        // Activity Logs
        self.activityLogs = m.prop();
        self.showMoreActivityLogs = m.prop(null);
        self.getLogs = function _getLogs (nodeId, link, addToExistingList) {
            var url = link || $osf.apiV2Url('nodes/' + nodeId + '/logs/', { query : { 'page[size]' : 6, 'embed' : ['nodes', 'user', 'linked_node', 'template_node']}});
            var promise = m.request({method : 'GET', url : url, config : xhrconfig});
            promise.then(function(result){
                result.data.map(function(log){
                    log.attributes.formattableDate = new $osf.FormattableDate(log.attributes.date);
                    if(addToExistingList){
                        self.activityLogs().push(log);
                    }
                });
                if(!addToExistingList){
                    self.activityLogs(result.data);  // Set activity log data
                }
                self.showMoreActivityLogs(result.links.next); // Set view for show more button
            });
            return promise;
        };
        // separate concerns, wrap getlogs here to get logs for the selected item
        self.getCurrentLogs = function _getCurrentLogs ( ){
            if(self.selected().length === 1){
                var id = self.selected()[0].data.id;
                var promise = self.getLogs(id);
            }
        };

        /* filesData is the link that loads tree data. This function refreshes that information. */
        self.updateFilesData = function(linkObject) {
            if (linkObject.link !== self.currentLink) {
                self.updateBreadcrumbs(linkObject);
                self.updateList(linkObject);
                self.currentLink = linkObject.link;
            }
            self.showSidebar(false);
        };

        // INFORMATION PANEL
        /* Defines the current selected item so appropriate information can be shown */
        self.selected = m.prop([]);
        self.updateSelected = function(selectedList){
            self.selected(selectedList);
            self.getCurrentLogs();
        };

        // USER FILTER
        self.activeFilter = m.prop({});
        self.updateFilter = function(filter) {
            self.activeFilter(filter);
            self.updateFilesData(filter);
        };

        self.removeProjectFromCollections = function _removeProjectFromCollection () {
            // Removes selected items from collect
            var collection = self.activeFilter().data.node;
            self.selected().map(function(item){
                m.request({
                    method : 'DELETE',
                    url : collection.links.self + 'node_links/' + item.data.id + '/',
                    config : xhrconfig
                }).then(function(result){
                    console.log(result);
                }, function(result){
                    console.log(result);
                });
            });
        };
        // GETTING THE NODES
        self.updateList = function(linkObject, success, error){
            self.refreshView(true);
            if(linkObject.data.systemCollection === 'nodes' && self.allProjectsLoaded()){
                self.data(self.allProjects());
                self.reload(true);
                self.refreshView(false);
                return;
            }
            if (success === undefined){
                success = self.updateListSuccess;
            }
            if(linkObject.data.systemCollection === 'nodes'){
                self.loadingNodes = true;
            }
            if (error === undefined){
                error = self.updateListError;
            }
            var url = linkObject.link;
            if (typeof url !== 'string'){
                throw new Error('Url argument for updateList needs to be string');
            }
            var promise = m.request({method : 'GET', url : url, config : xhrconfig});
            promise.then(success, error);
            return promise;
        };
        self.updateListSuccess = function(value) {
            value = self.addTbProperties(value);
            if(self.loadingPages){
                self.data().data = self.data().data.concat(value.data);
            } else {
                self.data(value);
            }
            if(!value.data[0]){ // If we have projects
                var lastcrumb = self.breadcrumbs()[self.breadcrumbs().length-1];
                if(lastcrumb.type === 'collection'){
                    if(lastcrumb.data.systemCollection === 'nodes'){
                        self.nonLoadTemplate(m('.fb-non-load-template.m-md.p-md.osf-box',
                            'You have notcreated any projects yet.'));
                    } else if (lastcrumb.data.systemCollection === 'registrations'){
                        self.nonLoadTemplate(m('.fb-non-load-template.m-md.p-md.osf-box',
                            'You have not made any registrations yet.'));
                    } else {
                        self.nonLoadTemplate(m('.fb-non-load-template.m-md.p-md.osf-box',
                            'This collection has no projects. To add projects go to "All My Projects" collection; drag and drop projects into the collection link'));
                    }
                } else {
                    self.nonLoadTemplate(m('.fb-non-load-template.m-md.p-md.osf-box.text-center', [
                        'This project has no subcomponents.',
                        m.component(AddProject, {
                            buttonTemplate : m('.btn.btn-link[data-toggle="modal"][data-target="#addSubcomponent"]', 'Add new Subcomponent'),
                            parentID : self.breadcrumbs()[self.breadcrumbs().length-1].data.id,
                            modalID : 'addSubcomponent',
                            stayCallback : function () {
                                self.allProjectsLoaded(false);
                                self.updateList(self.breadcrumbs()[self.breadcrumbs().length-1]);
                            }
                        })
                    ]));
                }
            }
            // if we have more pages keep loading the pages
            if (value.links.next) {
                self.loadingPages = true;
                var collData = {};
                if(!self.allProjectsLoaded()) {
                    collData = { systemCollection : 'nodes' };
                }
                self.updateList({link : value.links.next, data : collData });
                return; // stop here so the reloads below don't run
            } else {
                self.loadingPages = false;
            }
            if(self.loadingNodes) {
                self.data().data = _makeTree(self.data().data);
                self.allProjects(self.data());
                self.generateFiltersList();
                self.loadingNodes = false;
                self.allProjectsLoaded(true);
            }
            self.reload(true);
            self.refreshView(false);
        };
        self.updateListError = function(result){
            self.nonLoadTemplate(m('.fb-error.text-danger.m-t-lg', [
                m('p', m('i.fa.fa-exclamation-circle')),
                m('p','Projects for this selection couldn\'t load.'),
                m('p', m('.btn.btn-default', { onclick : self.updateFilter.bind(null, self.systemCollections[0])},' Reload \'All My Projects\''))
            ]));
            self.data().data = [];
            console.error(result);
            self.refreshView(false);
            throw new Error('Receiving initial data for File Browser failed. Please check your url');
        };
        self.generateFiltersList = function _generateFilterList () {
            self.users = {};
            self.tags = {};
            self.data().data.map(function(item){
                var contributors = item.embeds.contributors.data;
                for(var i = 0; i < contributors.length; i++) {
                    var u = contributors[i];
                    if(self.users[u.id] === undefined) {
                        self.users[u.id] = {
                            data : u,
                            count: 1
                        };
                    } else {
                        self.users[u.id].count++;
                    }
                }

                var tags = item.attributes.tags;
                for(var j = 0; j < tags.length; j++) {
                    var t = tags[j];
                    if(self.tags[t] === undefined) {
                        self.tags[t] = 1;
                    } else {
                        self.tags[t]++;
                    }
                }
            });

            // Add to lists with numbers
            for (var user in self.users){
                var u2 = self.users[user];
                self.nameFilters.push(new LinkObject('name', { id : u2.data.id, count : u2.count, query : { 'related_counts' : true }}, u2.data.embeds.users.data.attributes.full_name));
            }
            for (var tag in self.tags){
                var t2 = self.tags[tag];
                self.tagFilters.push(new LinkObject('tag', { tag : tag, count : t2, query : { 'related_counts' : true }}, tag));
            }
            console.log(self.data().data, self.users, self.tags);
        };

        // BREADCRUMBS
        self.updateBreadcrumbs = function(linkObject){
            if (linkObject.type === 'collection' || linkObject.type === 'name' || linkObject.type === 'tag'){
                self.breadcrumbs([linkObject]);
                return;
            }
            if (linkObject.placement === 'breadcrumb'){
                self.breadcrumbs().splice(linkObject.index+1, self.breadcrumbs().length-linkObject.index-1);
                return;
            }
            if(linkObject.ancestors.length > 0){
                linkObject.ancestors.forEach(function(item){
                    var ancestorLink = new LinkObject('node', item.data, item.data.name);
                    self.breadcrumbs().push(ancestorLink);
                });
            }
            self.breadcrumbs().push(linkObject);
        }.bind(self);

        self.sidebarInit = function (element, isInit) {
            if(!isInit){
                $('[data-toggle="tooltip"]').tooltip();
            }
        };

        self.init = function () {
            self.updateList(self.systemCollections[0]);
        };
        self.init();
    },
    view : function (ctrl, args) {
        var mobile = window.innerWidth < 767; // true if mobile view
        var infoPanel = '';
        var poStyle = 'width : 72%'; // Other percentages are set in CSS in file-browser.css These are here because they change
        var sidebarButtonClass = 'btn-default';
        if (ctrl.showInfo() && !mobile){
            infoPanel = m('.fb-infobar', m.component(Information, ctrl));
            poStyle = 'width : 47%';
        }
        if(ctrl.showSidebar()){
            sidebarButtonClass = 'btn-primary';
        }
        if (mobile) {
            poStyle = 'width : 100%';
        } else {
            ctrl.showSidebar(true);
        }
        return [
            m('.fb-header.row', [
                m('.col-xs-12.col-sm-6', m.component(Breadcrumbs,ctrl)),
                m('.fb-buttonRow.col-xs-12.col-sm-6', [
                    mobile ? m('button.btn.btn-sm.m-r-sm', {
                        'class' : sidebarButtonClass,
                        onclick : function () {
                            ctrl.showSidebar(!ctrl.showSidebar());
                        }
                    }, m('.fa.fa-bars')) : '',
                    m('span.m-r-md.hidden-xs', ctrl.data().data.length + ' Projects'),
                    m('#poFilter.m-r-xs')
                ])
            ]),
            ctrl.showSidebar() ?
            m('.fb-sidebar', { config : ctrl.sidebarInit}, [
                mobile ? [ m('.fb-dismiss', m('button.close[aria-label="Close"]', {
                    onclick : function () {
                        ctrl.showSidebar(false);
                    }
                }, [
                    m('span[aria-hidden="true"]','×')
                ])),
                    m('p.p-sm.text-center.text-muted', [
                        'Select a list below to see the projects. or click ',
                        m('i.fa.fa-bars'),
                        ' button above to toggle.'
                    ])
                ] : '',
                m.component(Collections, ctrl),
                m.component(Filters, {
                    activeFilter : ctrl.activeFilter,
                    updateFilter : ctrl.updateFilter,
                    nameFilters : ctrl.nameFilters,
                    tagFilters : ctrl.tagFilters
                })
            ]) : '',
            mobile && ctrl.showSidebar() ? '' : m('.fb-main', { style : poStyle },[
                ctrl.refreshView() ? m('.spinner-div', m('i.fa.fa-refresh.fa-spin')) : '',
                ctrl.data().data.length === 0 ? ctrl.nonLoadTemplate() : m('#poOrganizer',  m.component( ProjectOrganizer, {
                        filesData : ctrl.data,
                        updateSelected : ctrl.updateSelected,
                        updateFilesData : ctrl.updateFilesData,
                        LinkObject : LinkObject,
                        reload : ctrl.reload,
                        dragContainment : args.wrapperSelector,
                        allProjects : ctrl.allProjects
                    })
                )
            ]),
            mobile ? '' : m('.fb-info-toggle',{
                    onclick : function(){
                        ctrl.showInfo(!ctrl.showInfo());
                    }
                },
                ctrl.showInfo() ? m('i.fa.fa-chevron-right') :  m('i.fa.fa-chevron-left')
            ),
            infoPanel,
            m.component(Modals, ctrl)
        ];
    }
};

/**
 * Collections Module.
 * @constructor
 */
var Collections  = {
    controller : function(args){
        var self = this;
        self.newCollectionName = m.prop('');
        self.newCollectionRename = m.prop('');
        self.dismissModal = function () {
            $('.modal').modal('hide');
        };
        self.currentPage = m.prop(1);
        self.totalPages = m.prop(1);
        self.calculateTotalPages = function(result){
            if(result){ // If this calculation comes after GET call to collections
                self.totalPages(Math.ceil((result.links.meta.total + args.systemCollections.length)/self.pageSize()));
            } else {
                self.totalPages(Math.ceil((self.collections().length)/self.pageSize()));
            }
        };
        self.pageSize = m.prop(5);
        self.validation = m.prop(false);
        self.validationError = m.prop('');
        self.showCollectionMenu = m.prop(false); // Show hide ellipsis menu for collections
        self.collectionMenuObject = m.prop({item : {label:null}, x : 0, y : 0}); // Collection object to complete actions on menu
        self.resetCollectionMenu = function () {
            self.collectionMenuObject({item : {label:null}, x : 0, y : 0});
        };
        self.updateCollectionMenu = function (item, event) {
            var offset = $(event.target).offset();
            var x = offset.left;
            var y = offset.top;
            if (event.view.innerWidth < 767){
                x = x-105; // width of this menu plus padding
                y = y-270; // fixed height from collections parent to top with adjustments for this menu div
            }
            self.showCollectionMenu(true);
            item.renamedLabel = item.label;
            self.collectionMenuObject({
                item : item,
                x : x,
                y : y
            });
        };
        // Default system collections
        self.collections = m.prop([
            new LinkObject('collection', { path : 'users/me/nodes/', query : { 'related_counts' : true, 'page[size]'  : 12, 'embed' : 'contributors' }, systemCollection : 'nodes'}, 'All My Projects'),
            new LinkObject('collection', { path : 'users/me/registrations/', query : { 'related_counts' : true, 'page[size]'  : 12, 'embed' : 'contributors'}, systemCollection : 'registrations'}, 'All My Registrations')
        ]);
        // Load collection list
        var loadCollections = function(url){
            var promise = m.request({method : 'GET', url : url, config : xhrconfig});
            promise.then(function(result){
                result.data.forEach(function(node){
                    var count = node.relationships.linked_nodes.links.related.meta.count;
                    self.collections().push(new LinkObject('collection', { path : 'collections/' + node.id + '/linked_nodes/', query : { 'related_counts' : true, 'embed' : 'contributors' }, systemCollection : false, node : node, count : m.prop(count) }, node.attributes.title));
                });
                if(result.links.next){
                    loadCollections(result.links.next);
                }
            });
            promise.then(self.calculateTotalPages());
        };
        var collectionsUrl = $osf.apiV2Url('collections/', { query : {'related_counts' : true, 'page[size]' : self.pageSize(), 'sort' : 'date_created', 'embed' : 'node_links'}});
        loadCollections(collectionsUrl);
        args.activeFilter(self.collections()[0]);

        self.addCollection = function () {
            console.log( self.newCollectionName());
            var url = $osf.apiV2Url('collections/', {});
            var data = {
                'data': {
                    'type': 'collections',
                    'attributes': {
                        'title': self.newCollectionName(),
                    }
                }
            };
            var promise = m.request({method : 'POST', url : url, config : xhrconfig, data : data});
            promise.then(function(result){
                console.log(result);
                var node = result.data;
                var count = node.relationships.linked_nodes.links.related.meta.count
                self.collections().push(new LinkObject('collection', { path : 'collections/' + node.id + '/linked_nodes/', query : { 'related_counts' : true }, systemCollection : false, node : node, count : m.prop(count) }, node.attributes.title));
                args.sidebarInit();
            });
            self.newCollectionName('');
            self.dismissModal();
            self.calculateTotalPages();
            return promise;
        };
        self.deleteCollection = function(){
            var url = self.collectionMenuObject().item.data.node.links.self;
            var promise = m.request({method : 'DELETE', url : url, config : xhrconfig});
            promise.then(function(result){
                for ( var i = 0; i < self.collections().length; i++) {
                    var item = self.collections()[i];
                    if (item.data.node && item.data.node.id === self.collectionMenuObject().item.data.node.id){
                        self.collections().splice(i, 1);
                        break;
                    }
                }
            });
            self.dismissModal();
            self.calculateTotalPages();
            return promise;
        };
        self.renameCollection = function () {
            console.log(self.collectionMenuObject());
            var url = self.collectionMenuObject().item.data.node.links.self;
            var nodeId = self.collectionMenuObject().item.data.node.id;
            var title = self.collectionMenuObject().item.renamedLabel;
            var data = {
                'data': {
                    'type': 'collections',
                    'id':  nodeId,
                    'attributes': {
                        'title': title
                    }
                }
            };
            var promise = m.request({method : 'PATCH', url : url, config : xhrconfig, data : data});
            promise.then(function(result){
                console.log(url, result);
                self.collectionMenuObject().item.label = title;
                m.redraw(true);
            });
            self.dismissModal();
            return promise;
        };
        self.applyDroppable = function _applyDroppable ( ){
            $('.fb-collections ul>li').droppable({
                hoverClass: 'bg-color-hover',
                drop: function( event, ui ) {
                    console.log('dropped', event, ui, this);
                    var collection = self.collections()[$(this).attr('data-index')];
                    var dataArray = [];
                    // If multiple items are dragged they have to be selected to make it work
                    if (args.selected().length > 1) {
                        args.selected().map(function(item){
                            dataArray.push(buildCollectionNodeData(item.data.id));
                        });
                    } else {
                        // if single items are passed use the event information
                        dataArray.push(buildCollectionNodeData(ui.draggable.find('.title-text>a').attr('data-nodeID'))); // data-nodeID attribute needs to be set in project organizer building title column
                    }
                    function saveNodetoCollection (index) {
                        function doNext (){
                            if(dataArray[index+1]){
                                saveNodetoCollection(index+1);
                            }
                            collection.data.count(collection.data.count()+1);
                        }
                        m.request({
                            method : 'POST',
                            url : collection.data.node.links.self + 'node_links/', //collection.data.node.relationships.linked_nodes.links.related.href,
                            config : xhrconfig,
                            data : dataArray[index]
                        }).then(doNext, doNext); // In case of success or error. It doesn't look like mithril has a general .done method
                    }
                    if(dataArray.length > 0){
                        saveNodetoCollection(0);
                    }
                }
            });
        };
    },
    view : function (ctrl, args) {
        var selectedCSS;
        var submenuTemplate;
        var collectionList = function () {
            var item;
            var index;
            var list = [];
            var childCount;
            var begin = ((ctrl.currentPage()-1)*ctrl.pageSize()); // remember indexes start from 0
            var end = ((ctrl.currentPage()) *ctrl.pageSize()); // 1 more than the last item
            if (ctrl.collections().length < end) {
                end = ctrl.collections().length;
            }
            for (var i = begin; i < end; i++) {
                item = ctrl.collections()[i];
                index = i;
                childCount = item.data.count ? ' (' + item.data.count() + ')' : '';
                if (item.id === args.activeFilter().id) {
                    selectedCSS = 'active';
                } else if (item.id === ctrl.collectionMenuObject().item.id) {
                    selectedCSS = 'bg-color-hover';
                } else {
                    selectedCSS = '';
                }
                if (!item.data.systemCollection) {
                    submenuTemplate = m('i.fa.fa-ellipsis-v.pull-right.text-muted.p-xs', {
                        'data-index' : i,
                        onclick : function (e) {
                            var index = $(this).attr('data-index');
                            var selectedItem = ctrl.collections()[index];
                            ctrl.updateCollectionMenu(selectedItem, e);
                        }
                    });
                } else {
                    submenuTemplate = '';
                }
                list.push(m('li', { className : selectedCSS, 'data-index' : index },
                    [
                        m('a', { href : '#', onclick : args.updateFilter.bind(null, item) },  item.label + childCount ),
                        submenuTemplate
                    ]
                ));
            }
            return list;
        };
        var collectionListTemplate = [
            m('h5', [
                'Collections ',
                m('i.fa.fa-question-circle.text-muted', {
                    'data-toggle':  'tooltip',
                    'title':  'Collections are groups of projects. You can create new collections and add any project you are a collaborator on or a public project.',
                    'data-placement' : 'bottom'
                }, ''),
                m('.pull-right', [
                    m('button.btn.btn-xs.btn-success[data-toggle="modal"][data-target="#addColl"]', m('i.fa.fa-plus')),
                    m.component(MicroPagination, { currentPage : ctrl.currentPage, totalPages : ctrl.totalPages })
                    ]
                )
            ]),
            m('ul', { config: ctrl.applyDroppable },[
                collectionList(),
                ctrl.showCollectionMenu() ? m('.collectionMenu',{
                    style : 'position:absolute;top: ' + ctrl.collectionMenuObject().y + 'px;left: ' + ctrl.collectionMenuObject().x + 'px;'
                }, [
                    m('.menuClose', { onclick : function (e) {
                        ctrl.showCollectionMenu(false);
                        ctrl.resetCollectionMenu();
                    }
                    }, m('.text-muted','×')),
                    m('ul', [
                        m('li[data-toggle="modal"][data-target="#renameColl"].pointer',{
                            onclick : function (e) {
                                ctrl.showCollectionMenu(false);
                            }
                        }, [
                            m('i.fa.fa-pencil'),
                            ' Rename'
                        ]),
                        m('li[data-toggle="modal"][data-target="#removeColl"].pointer',{
                            onclick : function (e) {
                                ctrl.showCollectionMenu(false);
                            }
                        }, [
                            m('i.fa.fa-trash'),
                            ' Delete'
                        ])
                    ])
                ]) : ''
            ])
        ];
        return m('.fb-collections', [
            collectionListTemplate,
            m('.fb-collections-modals', [
                m('#addColl.modal.fade[tabindex=-1][role="dialog"][aria-labelledby="addCollLabel"][aria-hidden="true"]',
                    m('.modal-dialog',
                        m('.modal-content', [
                            m('.modal-header', [
                                m('button.close[data-dismiss="modal"][aria-label="Close"]', [
                                    m('span[aria-hidden="true"]','×')
                                ]),
                                m('h3.modal-title#addCollLabel', 'Add New Collection')
                            ]),
                            m('.modal-body', [
                                m('p', 'Collections are groups of projects that help you organize your work. After you create your collection you can add projects by dragging and dropping projects to the collection. '),
                                m('.form-inline', [
                                    m('.form-group', [
                                        m('label[for="addCollInput]', 'Collection Name'),
                                        m('input[type="text"].form-control.m-l-sm#addCollInput', {
                                            onkeyup: function (ev){
                                                var val = $(this).val();
                                                if (val === 'Bookmarks') {
                                                    ctrl.validation(false);
                                                    ctrl.validationError('Your collection name can\'t be "Bookmarks", because bookmarks feature requires this name. Please select any other name. ');
                                                } else {
                                                    ctrl.validationError('');
                                                    if(val.length > 0) {
                                                        ctrl.validation(true);
                                                    } else {
                                                        ctrl.validation(false);
                                                    }
                                                }


                                                if(ctrl.validation()){
                                                    if(ev.which === 13){
                                                        ctrl.addCollection();
                                                    }
                                                }
                                                ctrl.newCollectionName(val);
                                            },
                                            value : ctrl.newCollectionName()
                                        }),
                                        m('span.help-block', ctrl.validationError())
                                    ])
                                ]),
                            ]),
                            m('.modal-footer', [
                                m('button[type="button"].btn.btn-default[data-dismiss="modal"]',
                                    {
                                        onclick : function(){
                                            ctrl.dismissModal();
                                            ctrl.newCollectionName('');
                                        }
                                    }, 'Cancel'),
                                ctrl.validation() ? m('button[type="button"].btn.btn-success', { onclick : ctrl.addCollection },'Add')
                                    : m('button[type="button"].btn.btn-success[disabled]', { onclick : ctrl.addCollection },'Add')
                            ])
                        ])
                    )
                ),
                m('#renameColl.modal.fade[tabindex=-1][role="dialog"][aria-labelledby="renameCollLabel"][aria-hidden="true"]',
                    m('.modal-dialog',
                        m('.modal-content', [
                            m('.modal-header', [
                                m('button.close[data-dismiss="modal"][aria-label="Close"]', [
                                    m('span[aria-hidden="true"]','×')
                                ]),
                                m('h3.modal-title#renameCollLabel', 'Rename Collection')
                            ]),
                            m('.modal-body', [
                                m('.form-inline', [
                                    m('.form-group', [
                                        m('label[for="addCollInput]', 'Rename to: '),
                                        m('input[type="text"].form-control.m-l-sm#renameCollInput',{
                                            onkeyup: function(ev){
                                                if (ev.which === 13) { // if enter is pressed
                                                    ctrl.renameCollection();
                                                }
                                                ctrl.collectionMenuObject().item.renamedLabel = $(this).val();
                                            },
                                            value: ctrl.collectionMenuObject().item.renamedLabel})

                                    ])
                                ])
                            ]),
                            m('.modal-footer', [
                                m('button[type="button"].btn.btn-default[data-dismiss="modal"]', 'Cancel'),
                                m('button[type="button"].btn.btn-success', {
                                    onclick : ctrl.renameCollection
                                },'Rename')
                            ])
                        ])
                    )
                ),
                m('#removeColl.modal.fade[tabindex=-1][role="dialog"][aria-labelledby="removeCollLabel"][aria-hidden="true"]',
                    m('.modal-dialog',
                        m('.modal-content', [
                            m('.modal-header', [
                                m('button.close[data-dismiss="modal"][aria-label="Close"]', [
                                    m('span[aria-hidden="true"]','×')
                                ]),
                                m('h3.modal-title#removeCollLabel', 'Delete Collection "' + ctrl.collectionMenuObject().item.label + '"?')
                            ]),
                            m('.modal-body', [
                                m('p', 'This will delete your collection but your projects will not be deleted.'),

                            ]),
                            m('.modal-footer', [
                                m('button[type="button"].btn.btn-default[data-dismiss="modal"]', 'Cancel'),
                                m('button[type="button"].btn.btn-danger', {
                                    onclick : ctrl.deleteCollection
                                },'Delete')
                            ])
                        ])
                    )
                )
            ])
        ]);
    }
};
/**
 * Small view component for compact pagination
 * Requires currentPage and totalPages to be m.prop
 * @type {{view: MicroPagination.view}}
 */
var MicroPagination = {
    view : function(ctrl, args) {
        return m('span.m-l-xs', [
            m('span.btn.btn-xs.btn-default.m-r-xs', { onclick : function(){
                if(args.currentPage() > 1){
                    args.currentPage(args.currentPage() - 1);
                }
            }}, m('i.fa.fa-angle-left.text-muted')),
            m('span', args.currentPage() + '/' + args.totalPages()),
            m('span.btn.btn-xs.btn-default.m-l-xs', { onclick : function(){
                if(args.currentPage() < args.totalPages()) {
                    args.currentPage(args.currentPage() + 1);
                }
            }}, m('i.fa.fa-angle-right.text-muted'))
        ]);
    }
};

/**
 * Breadcrumbs Module
 * @constructor
 */

var Breadcrumbs = {
    view : function (ctrl, args) {
        var mobile = window.innerWidth < 767; // true if mobile view
        var items = args.data();
        if (mobile && items.length > 1) {
            return m('.fb-breadcrumbs', [
                m('ul', [
                    m('li', [
                        m('.btn.btn-link[data-toggle="modal"][data-target="#parentsModal"]', '...'),
                        m('i.fa.fa-angle-right')
                    ]),
                    m('li', m('span.btn', items[items.length-1].label)),
                ]),
                m('#parentsModal.modal.fade[tabindex=-1][role="dialog"][aria-hidden="true"]',
                    m('.modal-dialog',
                        m('.modal-content', [
                            m('.modal-body', [
                                m('button.close[data-dismiss="modal"][aria-label="Close"]', [
                                    m('span[aria-hidden="true"]','×'),
                                ]),
                                m('h4', 'Parent Projects'),
                                args.breadcrumbs().map(function(item, index, array){
                                    if(index === array.length-1){
                                        return m('.fb-parent-row.btn', {
                                            style : 'margin-left:' + (index*20) + 'px;',
                                        },  [
                                            m('i.fa.fa-angle-right.m-r-xs'),
                                            item.label
                                        ]);
                                    }
                                    item.index = index; // Add index to update breadcrumbs
                                    item.placement = 'breadcrumb'; // differentiate location for proper breadcrumb actions
                                    return m('.fb-parent-row',
                                        m('span.btn.btn-link', {
                                            style : 'margin-left:' + (index*20) + 'px;',
                                            onclick : function() {
                                                args.updateFilesData(item);
                                                $('.modal').modal('hide');
                                            }
                                        },  [
                                            m('i.fa.fa-angle-right.m-r-xs'),
                                            item.label
                                        ])
                                    );
                                })
                            ]),
                        ])
                    )
                )
            ]);
        }
        return m('.fb-breadcrumbs', m('ul', [
            args.breadcrumbs().map(function(item, index, array){
                if(index === array.length-1){
                    var addProjectTemplate = m.component(AddProject, {
                        buttonTemplate : m('.btn.btn-sm.text-muted[data-toggle="modal"][data-target="#addProject"]', [m('i.fa.fa-plus', { style: 'font-size: 10px;'}), ' Add Component']),
                        parentID : args.breadcrumbs()[args.breadcrumbs().length-1].data.id,
                        modalID : 'addProject',
                        stayCallback : function () {
                            args.allProjectsLoaded(false);
                            args.updateList(args.breadcrumbs()[args.breadcrumbs().length-1]);
                        }
                    });
                    return [
                        m('li',  [
                            m('span.btn', item.label),
                            m('i.fa.fa-angle-right')
                        ]),
                        item.type === 'node' ? addProjectTemplate : ''
                    ];
                }
                item.index = index; // Add index to update breadcrumbs
                item.placement = 'breadcrumb'; // differentiate location for proper breadcrumb actions
                return m('li',
                    m('span.btn.btn-link', { onclick : args.updateFilesData.bind(null, item)},  item.label),
                    m('i.fa.fa-angle-right')
                );
            }),


        ]));
    }
};


/**
 * Filters Module.
 * @constructor
 */
var Filters = {
    controller : function (args) {
        var self = this;
        self.nameCurrentPage = m.prop(1);
        self.namePageSize = m.prop(4);
        self.nameTotalPages = m.prop(Math.ceil(args.nameFilters.length/self.namePageSize()));
        self.tagCurrentPage = m.prop(1);
        self.tagPageSize = m.prop(4);
        self.tagTotalPages = m.prop(Math.ceil(args.tagFilters.length/self.tagPageSize()));
    },
    view : function (ctrl, args) {
        var selectedCSS;
        var returnNameFilters = function (){
            var list = [];
            var begin = ((ctrl.nameCurrentPage()-1) * ctrl.namePageSize()); // remember indexes start from 0
            var end = ((ctrl.nameCurrentPage()) * ctrl.namePageSize()); // 1 more than the last item
            if (args.nameFilters.length < end) {
                end = args.nameFilters.length;
            }
            for (var i = begin; i < end; i++) {
                var item = args.nameFilters[i];
                selectedCSS = item.id === args.activeFilter().id ? '.active' : '';
                list.push(m('li' + selectedCSS,
                    m('a', { href : '#', onclick : args.updateFilter.bind(null, item)},
                        item.label + ' (' + item.data.count + ')'
                    )
                ));
            }
            return list;
        };
        var returnTagFilters = function(){
            var list = [];
            var begin = ((ctrl.tagCurrentPage()-1) * ctrl.tagPageSize()); // remember indexes start from 0
            var end = ((ctrl.tagCurrentPage()) * ctrl.tagPageSize()); // 1 more than the last item
            if (args.tagFilters.length < end) {
                end = args.tagFilters.length;
            }
            for (var i = begin; i < end; i++) {
                var item = args.tagFilters[i];
                selectedCSS = item.id === args.activeFilter().id ? '.active' : '';
                list.push(m('li' + selectedCSS,
                    m('a', { href : '#', onclick : args.updateFilter.bind(null, item)},
                        item.label + ' (' + item.data.count + ')'
                    )
                ));
            }
            return list;
        };
        return m('.fb-filters.m-t-lg',
            [
                m('h5', [
                    'Contributors',
                    m('.pull-right', m.component(MicroPagination, { currentPage : ctrl.nameCurrentPage, totalPages : ctrl.nameTotalPages }))
                ]),
                m('ul', [
                    returnNameFilters()
                ]),
                m('h5', [
                    'Tags',
                    m('.pull-right',m.component(MicroPagination, { currentPage : ctrl.tagCurrentPage, totalPages : ctrl.tagTotalPages }))
                ]), m('ul', [
                    returnTagFilters()
                ])
            ]
        );
    }
};

/**
 * Information Module.
 * @constructor
 */
var Information = {
    view : function (ctrl, args) {
        var template = '';
        var filter = args.activeFilter();
        if (args.selected().length === 1) {
            var item = args.selected()[0].data;
            template = m('.p-sm', [
                filter.type === 'collection' && !filter.data.systemCollection ? m('.fb-info-remove.p-xs.text-danger', { onclick : args.removeProjectFromCollections }, 'Remove from collection') : '',
                m('h3', m('a', { href : item.links.html}, item.attributes.title)),
                m('[role="tabpanel"]', [
                    m('ul.nav.nav-tabs.m-b-md[role="tablist"]', [
                        m('li[role="presentation"].active', m('a[href="#tab-information"][aria-controls="information"][role="tab"][data-toggle="tab"]', 'Information')),
                        m('li[role="presentation"]', m('a[href="#tab-activity"][aria-controls="activity"][role="tab"][data-toggle="tab"]', { onclick : args.getCurrentLogs},'Activity')),
                    ]),
                    m('.tab-content', [
                        m('[role="tabpanel"].tab-pane.active#tab-information',[
                            m('p.fb-info-meta.text-muted', [
                                m('', 'Visibility : ' + (item.attributes.public ? 'Public' : 'Private')),
                                m('', 'Category: ' + item.attributes.category),
                                m('', 'Last Modified on: ' + item.date.local)
                            ]),
                            m('p', [
                                m('span', item.attributes.description)
                            ]),
                            item.attributes.tags.length > 0 ?
                            m('p.m-t-md', [
                                m('h5', 'Tags'),
                                item.attributes.tags.map(function(tag){
                                    return m('span.tag', tag);
                                })
                            ]) : '',
                            m('p.m-t-md', [
                                m('h5', 'Jump to Page'),
                                m('a.p-xs', { href : item.links.html + 'wiki/home'}, 'Wiki'),
                                m('a.p-xs', { href : item.links.html + 'files/'}, 'Files'),
                                m('a.p-xs', { href : item.links.html + 'settings/'}, 'Settings'),
                            ])
                        ]),
                        m('[role="tabpanel"].tab-pane#tab-activity',[
                            m.component(ActivityLogs, args)
                        ])
                    ])
                ])
            ]);
        }
        if (args.selected().length > 1) {
            template = m('.p-sm', [ '', args.selected().map(function(item){
                return m('.fb-info-multi', [
                    m('h4', m('a', { href : item.data.links.html}, item.data.attributes.title)),
                    m('p.fb-info-meta.text-muted', [
                        m('span', item.data.attributes.public ? 'Public' : 'Private' + ' ' + item.data.attributes.category),
                        m('span', ', Last Modified on ' + item.data.date.local)
                    ]),
                ]);
            })]);
        }
        return m('.fb-information', template);
    }
};


var ActivityLogs = {
    view : function (ctrl, args) {
        return m('.fb-activity-list.m-t-md', [
            args.activityLogs() ? args.activityLogs().map(function(item){
                return m('.fb-activity-item', [
                    m('', [ m('.fb-log-avatar.m-r-xs', m('img', { src : item.embeds.user.data.links.profile_image})), m.component(LogText,item)]),
                    m('.text-right', m('span.text-muted.m-r-xs', item.attributes.formattableDate.local))
                ]);
            }) : '',
            m('.fb-activity-nav.text-center', [
                args.showMoreActivityLogs() ? m('.btn.btn-sm.btn-link', { onclick: function(){ args.getLogs(null, args.showMoreActivityLogs(), true); }}, [ 'Show more', m('i.fa.fa-caret-down.m-l-xs')]) : '',
            ])

        ]);
    }
};

/**
 * Modals views.
 * @constructor
 */

var Modals = {
    view : function(ctrl, args) {
        return m('.fb-Modals', [
            m('#infoModal.modal.fade[tabindex=-1][role="dialog"][aria-hidden="true"]',
                m('.modal-dialog',
                    m('.modal-content', [
                        m('.modal-body', [
                            m('button.close[data-dismiss="modal"][aria-label="Close"]', [
                                m('span[aria-hidden="true"]','×'),
                            ]),
                            m.component(Information, args)
]),
                    ])
                )
            )
        ]);
    }
};

module.exports = { FileBrowser : FileBrowser, LinkObject: LinkObject };