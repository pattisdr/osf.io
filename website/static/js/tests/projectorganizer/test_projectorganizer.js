QUnit.test('1 equals "1"', function (assert) {
    assert.ok(1 == "1", "Passed!");
});


QUnit.module("AJAX Tests", {
    setup: function () {
        $.mockjax({
            url: '/api/v1/dashboard/get_dashboard/',
            responseTime: 0,
            contentType: 'text/json',
            responseText: {"data": [{"contributors": [{"url": "/k62ps/", "name": "McTestperson"}], "isFolder": true, "children": [], "isDashboard": true, "modifiedDelta": -5575.910912, "modifiedBy": "McTestperson", "registeredMeta": {}, "dateModified": "2014-07-08T16:06:19.301000", "description": null, "isProject": true, "node_id": "5wha8", "expand": true, "permissions": {"copyable": false, "edit": true, "acceptsCopies": true, "acceptsMoves": true, "acceptsFolders": true, "movable": false, "acceptsComponents": true, "view": true}, "kind": "folder", "name": "Dashboard", "isComponent": false, "parentIsFolder": false, "isRegistration": false, "apiURL": "/api/v1/project/5wha8/", "urls": {"upload": null, "fetch": null}, "isFile": false, "isPointer": false, "isSmartFolder": false}]}
        });
        $.mockjax({
            url: '/api/v1/dashboard/get_dashboard/5wha8',
            responseTime: 0,
            contentType: 'text/json',
            responseText: {"data": [{"contributors": [{"url": "/k62ps/", "name": "McTestperson"}], "isFolder": true, "children": [], "isDashboard": false, "modifiedDelta": -25.646482, "modifiedBy": "McTestperson", "registeredMeta": {}, "dateModified": "2014-07-08T18:52:16.203000", "description": null, "isProject": true, "node_id": "9gm2w", "expand": false, "permissions": {"copyable": false, "edit": true, "acceptsCopies": true, "acceptsMoves": true, "acceptsFolders": true, "movable": true, "acceptsComponents": true, "view": true}, "kind": "folder", "name": "2", "isComponent": false, "parentIsFolder": true, "isRegistration": false, "apiURL": "/api/v1/project/9gm2w/", "urls": {"upload": null, "fetch": null}, "isFile": false, "isPointer": true, "isSmartFolder": false}, {"contributors": [{"url": "/k62ps/", "name": "McTestperson"}], "isFolder": true, "children": [], "isDashboard": false, "modifiedDelta": -5300.049998, "modifiedBy": "McTestperson", "registeredMeta": {}, "dateModified": "2014-07-08T17:24:21.804000", "description": null, "isProject": true, "node_id": "zp6ji", "expand": true, "permissions": {"copyable": false, "edit": true, "acceptsCopies": true, "acceptsMoves": true, "acceptsFolders": true, "movable": true, "acceptsComponents": true, "view": true}, "kind": "folder", "name": "1", "isComponent": false, "parentIsFolder": true, "isRegistration": false, "apiURL": "/api/v1/project/zp6ji/", "urls": {"upload": null, "fetch": null}, "isFile": false, "isPointer": true, "isSmartFolder": false}, {"kind": "folder", "name": "All my projects", "contributors": [], "parentIsFolder": true, "isPointer": false, "isFolder": true, "dateModified": null, "modifiedDelta": 0, "node_id": "-amp", "modifiedBy": null, "isSmartFolder": true, "urls": {"upload": null, "fetch": null}, "isDashboard": false, "children": [], "expand": false, "permissions": {"edit": false, "acceptsDrops": false, "copyable": false, "movable": false, "view": true}}, {"kind": "folder", "name": "All my registrations", "contributors": [], "parentIsFolder": true, "isPointer": false, "isFolder": true, "dateModified": null, "modifiedDelta": 0, "node_id": "-amr", "modifiedBy": null, "isSmartFolder": true, "urls": {"upload": null, "fetch": null}, "isDashboard": false, "children": [], "expand": false, "permissions": {"edit": false, "acceptsDrops": false, "copyable": false, "movable": false, "view": true}}]}
        });
        $.mockjax({
            url: '/api/v1/dashboard/get_dashboard/-amp',
            responseTime: 0,
            contentType: 'text/json',
            responseText: [{"contributors": [{"url": "/k62ps/", "name": "McTestperson"}, {"url": "/nqt8y/", "name": "Barrows"}], "isFolder": false, "children": [], "isDashboard": false, "modifiedDelta": -5425.354011, "modifiedBy": "McTestperson", "registeredMeta": {}, "dateModified": "2014-07-08T16:14:01.947000", "description": "optimize user-centric e-services", "isProject": true, "node_id": "i5yj3", "expand": true, "permissions": {"copyable": true, "edit": true, "acceptsCopies": true, "acceptsMoves": false, "acceptsFolders": false, "movable": false, "acceptsComponents": false, "view": true}, "kind": "folder", "name": "Right-sized demand-driven budgetarymanagement", "isComponent": false, "parentIsFolder": false, "isRegistration": false, "apiURL": "/api/v1/project/i5yj3/", "urls": {"upload": null, "fetch": "/i5yj3/"}, "isFile": false, "isPointer": false, "isSmartFolder": false}]
        });
        $.mockjax({
            url: '/api/v1/dashboard/get_dashboard/-amr',
            responseTime: 0,
            contentType: 'text/json',
            responseText: [{"contributors": [{"url": "/k62ps/", "name": "McTestperson"}, {"url": "/nqt8y/", "name": "Barrows"}], "isFolder": false, "children": [], "isDashboard": false, "modifiedDelta": -5501.727837, "modifiedBy": "McTestperson", "registeredMeta": {"Open-Ended_Registration": "{\"summary\": \"Testing\"}"}, "dateModified": "2014-07-08T16:14:01.947000", "description": "optimize user-centric e-services", "isProject": true, "node_id": "f9nhw", "expand": true, "permissions": {"copyable": true, "edit": false, "acceptsCopies": true, "acceptsMoves": false, "acceptsFolders": false, "movable": false, "acceptsComponents": false, "view": true}, "kind": "folder", "name": "Right-sized demand-driven budgetarymanagement", "isComponent": false, "parentIsFolder": false, "isRegistration": true, "apiURL": "/api/v1/project/f9nhw/", "urls": {"upload": null, "fetch": "/f9nhw/"}, "isFile": false, "isPointer": false, "isSmartFolder": false}]
        });
        $.mockjax({
            url: '/api/v1/dashboard/get_dashboard/9gm2w',
            responseTime: 0,
            contentType: 'text/json',
            responseText: {"data": [{"contributors": [{"url": "/k62ps/", "name": "McTestperson"}], "isFolder": true, "children": [], "isDashboard": false, "modifiedDelta": -6843.890789, "modifiedBy": "McTestperson", "registeredMeta": {}, "dateModified": "2014-07-08T18:52:16.186000", "description": null, "isProject": true, "node_id": "39hen", "expand": false, "permissions": {"copyable": false, "edit": true, "acceptsCopies": true, "acceptsMoves": true, "acceptsFolders": true, "movable": true, "acceptsComponents": true, "view": true}, "kind": "folder", "name": "2-1", "isComponent": false, "parentIsFolder": true, "isRegistration": false, "apiURL": "/api/v1/project/39hen/", "urls": {"upload": null, "fetch": null}, "isFile": false, "isPointer": true, "isSmartFolder": false}]}
        });
        $.mockjax({
            url: '/api/v1/dashboard/get_dashboard/zp6ji',
            responseTime: 0,
            contentType: 'text/json',
            responseText: {"data": [{"contributors": [{"url": "/k62ps/", "name": "McTestperson"}, {"url": "/nqt8y/", "name": "Barrows"}], "isFolder": false, "children": [], "isDashboard": false, "modifiedDelta": -4213.664841, "modifiedBy": "McTestperson", "registeredMeta": {}, "dateModified": "2014-07-08T17:45:27.995000", "description": "optimize user-centric e-services", "isProject": true, "node_id": "i5yj3", "expand": true, "permissions": {"copyable": true, "edit": true, "acceptsCopies": true, "acceptsMoves": false, "acceptsFolders": false, "movable": true, "acceptsComponents": false, "view": true}, "kind": "folder", "name": "Right-sized demand-driven budgetarymanagement", "isComponent": false, "parentIsFolder": true, "isRegistration": false, "apiURL": "/api/v1/project/i5yj3/", "urls": {"upload": null, "fetch": "/i5yj3/"}, "isFile": false, "isPointer": true, "isSmartFolder": false}, {"contributors": [{"url": "/k62ps/", "name": "McTestperson"}], "isFolder": true, "children": [], "isDashboard": false, "modifiedDelta": -10167.873596, "modifiedBy": "McTestperson", "registeredMeta": {}, "dateModified": "2014-07-08T16:06:13.791000", "description": null, "isProject": true, "node_id": "4eyxz", "expand": true, "permissions": {"copyable": false, "edit": true, "acceptsCopies": true, "acceptsMoves": true, "acceptsFolders": true, "movable": true, "acceptsComponents": true, "view": true}, "kind": "folder", "name": "1-1", "isComponent": false, "parentIsFolder": true, "isRegistration": false, "apiURL": "/api/v1/project/4eyxz/", "urls": {"upload": null, "fetch": null}, "isFile": false, "isPointer": true, "isSmartFolder": false}]}
        });
        $.mockjax({
            url: '/api/v1/dashboard/get_dashboard/i5yj3',
            responseTime: 0,
            contentType: 'text/json',
            responseText: {"data": [{"contributors": [{"url": "/k62ps/", "name": "McTestperson"}], "isFolder": false, "children": [], "isDashboard": false, "modifiedDelta": -4267.079385, "modifiedBy": "McTestperson", "registeredMeta": {}, "dateModified": "2014-07-08T17:45:28.024000", "description": "visualize compelling solutions", "isProject": false, "node_id": "bzny3", "expand": false, "permissions": {"copyable": true, "edit": true, "acceptsCopies": false, "acceptsMoves": false, "acceptsFolders": false, "movable": false, "acceptsComponents": false, "view": true}, "kind": "item", "name": "Devolved heuristic array", "isComponent": true, "parentIsFolder": false, "isRegistration": false, "apiURL": "/api/v1/project/i5yj3/node/bzny3/", "urls": {"upload": null, "fetch": "/bzny3/"}, "isFile": false, "isPointer": false, "isSmartFolder": false}]}
        });
        $.mockjax({
            url: '/api/v1/dashboard/get_dashboard/f9nhw',
            responseTime: 0,
            contentType: 'text/json',
            responseText: {"data": [{"contributors": [{"url": "/k62ps/", "name": "McTestperson"}], "isFolder": false, "children": [], "isDashboard": false, "modifiedDelta": -5875.182537, "modifiedBy": "McTestperson", "registeredMeta": {"Open-Ended_Registration": "{\"summary\": \"Testing\"}"}, "dateModified": "2014-07-08T16:14:01.947000", "description": "visualize compelling solutions", "isProject": false, "node_id": "5xnai", "expand": false, "permissions": {"copyable": true, "edit": false, "acceptsCopies": false, "acceptsMoves": false, "acceptsFolders": false, "movable": false, "acceptsComponents": false, "view": true}, "kind": "item", "name": "Devolved heuristic array", "isComponent": true, "parentIsFolder": false, "isRegistration": true, "apiURL": "/api/v1/project/f9nhw/node/5xnai/", "urls": {"upload": null, "fetch": "/5xnai/"}, "isFile": false, "isPointer": false, "isSmartFolder": false}]}
        });
        $.mockjax({
            url: '/api/v1/dashboard/get_dashboard/4eyxz',
            responseTime: 0,
            contentType: 'text/json',
            responseText: {"data": [{"contributors": [{"url": "/k62ps/", "name": "McTestperson"}], "isFolder": true, "children": [], "isDashboard": false, "modifiedDelta": -6423.257029, "modifiedBy": "McTestperson", "registeredMeta": {}, "dateModified": "2014-07-08T16:06:13.772000", "description": null, "isProject": true, "node_id": "ti847", "expand": true, "permissions": {"copyable": false, "edit": true, "acceptsCopies": true, "acceptsMoves": true, "acceptsFolders": true, "movable": true, "acceptsComponents": true, "view": true}, "kind": "folder", "name": "1-1-1", "isComponent": false, "parentIsFolder": true, "isRegistration": false, "apiURL": "/api/v1/project/ti847/", "urls": {"upload": null, "fetch": null}, "isFile": false, "isPointer": true, "isSmartFolder": false}]}
        });
        $.mockjax({
            url: '/api/v1/dashboard/get_dashboard/bzny3',
            responseTime: 0,
            contentType: 'text/json',
            responseText: { "data": [] }
        });
        $.mockjax({
            url: '/api/v1/dashboard/get_dashboard/39hen',
            responseTime: 0,
            contentType: 'text/json',
            responseText: { "data": [] }
        });
        $.mockjax({
            url: '/api/v1/dashboard/get_dashboard/ti847',
            responseTime: 0,
            contentType: 'text/json',
            responseText: { "data": [] }
        });
        $.mockjax({
            url: '/api/v1/project/9gm2w/get_folder_pointers/',
            responseTime: 0,
            contentType: 'text/json',
            responseText: ["39hen"]
        });
        $.mockjax({
            url: '/api/v1/project/ti847/get_folder_pointers/',
            responseTime: 0,
            contentType: 'text/json',
            responseText: []
        });
        $.mockjax({
            url: '/api/v1/project/4eyxz/get_folder_pointers/',
            responseTime: 0,
            contentType: 'text/json',
            responseText: ["ti847"]
        });
        $.mockjax({
            url: '/api/v1/project/zp6ji/get_folder_pointers/',
            responseTime: 0,
            contentType: 'text/json',
            responseText: ["4eyxz", "i5yj3"]
        });
        $.mockjax({
            url: '/api/v1/project/5wha8/get_folder_pointers/',
            responseTime: 0,
            contentType: 'text/json',
            responseText: ["zp6ji", "9gm2w"]
        });
        $.mockjax({
            url: '/api/v1/project/39hen/get_folder_pointers/',
            responseTime: 0,
            contentType: 'text/json',
            responseText: []
        });
        $.mockjax({
            url: '/api/v1/project/*/collapse/',
            responseTime: 0,
            type: 'POST'
        });
        $.mockjax({
            url: '/api/v1/project/*/expand/',
            responseTime: 0,
            type: 'POST'
        });
    }
});


QUnit.asyncTest("Creates hgrid", function (assert) {
    expect(2);
    var runCount = 0;
    var $fixture = $('#qunit-fixutre');
    $fixture.append('<div id="project-grid" class="hgrid" ></div>');
    var projectbrowser = new ProjectOrganizer('#project-grid',
        {
            success: function () {
                var totalCallbacks = 4;
                if (runCount >= totalCallbacks) {
                    QUnit.start();
                    assert.ok(true, 'Success callback called ' + totalCallbacks + ' times.');
                    assert.notEqual($('#project-grid'), "");
                } else {
                    runCount++;
                }
            }
        });
});
