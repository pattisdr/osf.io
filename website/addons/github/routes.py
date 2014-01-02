"""

"""

from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer

from . import views

settings_routes = {
    'rules': [
        Rule([
            '/project/<pid>/settings/github/',
            '/project/<pid>/node/<nid>/settings/github/',
        ], 'post', views.github_settings, json_renderer),
        Rule([
            '/project/<pid>/settings/github/disable/',
            '/project/<pid>/node/<nid>/settings/github/disable/',
        ], 'post', views.github_disable, json_renderer),
        Rule([
            '/project/<pid>/github/file/<path:path>',
            '/project/<pid>/node/<nid>/github/file/<path:path>',
        ], 'get', views.github_download_file, json_renderer),
        Rule([
            '/project/<pid>/github/',
            '/project/<pid>/node/<nid>/github/',
        ], 'get', views.github_get_repo, json_renderer),
        Rule([
            '/project/<pid>/github/file/',
            '/project/<pid>/github/file/<path:path>',
            '/project/<pid>/node/<nid>/github/file/',
            '/project/<pid>/node/<nid>/github/file/<path:path>',
        ], 'post', views.github_upload_file, json_renderer),
        Rule([
            '/project/<pid>/github/file/<path:path>',
            '/project/<pid>/node/<nid>/github/file/<path:path>',
        ], 'delete', views.github_delete_file, json_renderer),
        Rule([
            '/project/<pid>/github/tarball/',
            '/project/<pid>/node/<nid>/github/tarball/',
        ], 'get', views.github_download_starball, json_renderer, {'archive': 'tar'}, endpoint_suffix='__tar'),
        Rule([
            '/project/<pid>/github/zipball/',
            '/project/<pid>/node/<nid>/github/zipball/',
        ], 'get', views.github_download_starball, json_renderer, {'archive': 'zip'}, endpoint_suffix='__zip'),
        Rule([
            '/project/<pid>/github/oauth/',
            '/project/<pid>/node/<nid>/github/oauth/',
        ], 'get', views.github_oauth_start, json_renderer),
        Rule([
            '/project/<pid>/github/oauth/delete/',
            '/project/<pid>/node/<nid>/github/oauth/delete/',
        ], 'post', views.github_oauth_delete, json_renderer),
        Rule('/addons/github/callback/<nid>/', 'get', views.github_oauth_callback, json_renderer),
    ],
    'prefix': '/api/v1',
}

page_routes = {
    'rules': [
        Rule([
            '/project/<pid>/github/',
            '/project/<pid>/node/<nid>/github/',
        ], 'get', views.github_page, OsfWebRenderer('project/addon.mako')),
    ],
}
