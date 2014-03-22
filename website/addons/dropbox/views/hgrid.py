# -*- coding: utf-8 -*-
import os
import logging

from website.project.decorators import must_be_contributor_or_public, must_have_addon
from website.util import rubeus

from website.addons.dropbox.client import get_node_client
from website.addons.dropbox.utils import (
    clean_path, list_dropbox_files, metadata_to_hgrid,
    build_dropbox_urls, clean_path
)

logger = logging.getLogger(__name__)
debug = logger.debug


@must_be_contributor_or_public
@must_have_addon('dropbox', 'node')
def dropbox_hgrid_data_contents(**kwargs):
    node_settings = kwargs['node_addon']
    node = node_settings.owner
    auth = kwargs['auth']
    path = kwargs.get('path', node_settings.folder)
    permissions = {
        'edit': node.can_edit(auth) and not node.is_registration,
        'view': node.can_view(auth)
    }
    client = get_node_client(node)
    contents = [metadata_to_hgrid(file_dict, node, permissions) for
            file_dict in client.metadata(path)['contents']]
    return contents


def dropbox_addon_folder(node_settings, auth, **kwargs):
    node = node_settings.owner
    path = clean_path(node_settings.folder)
    return [
        rubeus.build_addon_root(
            node_settings=node_settings,
            name=node_settings.folder,
            permissions=auth,
            nodeUrl=node.url,
            nodeApiUrl=node.api_url,
            urls={
                'upload': node.api_url_for('dropbox_upload',
                    path=path),
                'fetch': node.api_url_for('dropbox_hgrid_data_contents',
                    path=path)
            }
        )
    ]
