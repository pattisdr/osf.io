from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound

from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.wiki_versions.permissions import ContributorOrPublic, ExcludeWithdrawals
from api.wikis.serializers import (
    WikiVersionSerializer,
)

from framework.auth.oauth_scopes import CoreScopes
from addons.wiki.models import WikiVersion


class WikiVersionMixin(object):
    """Mixin with convenience methods for retrieving the wiki version based on the
    URL. By default, fetches the wiki version based on the wiki-version_id kwarg.
    """
    wiki_lookup_url_kwarg = 'wiki_version_id'

    def get_wiki_version(self, check_permissions=True):
        pk = self.kwargs[self.wiki_lookup_url_kwarg]
        wiki = WikiVersion.load(pk)
        if not wiki:
            raise NotFound

        if check_permissions:
            # May raise a permission denied
            self.check_object_permissions(self.request, wiki)
        return wiki


class WikiVersionDetail(JSONAPIBaseView, generics.RetrieveAPIView, WikiVersionMixin):
    """Details about a specific wiki version. *Read-only*.

    ###Permissions

    Wiki pages on public nodes are given read-only access to everyone. Wiki pages on private nodes are only visible to
    contributors and administrators on the parent node.

    Note that if an anonymous view_only key is being used, the user relationship will not be exposed.

    ##Relationships

    ###User

    The user who created the wiki.

    ###WikiPage

    The wiki that this version belongs to

    ##Links

        self:  the canonical api endpoint of this wiki

    ##Query Params

    *None*.

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ContributorOrPublic,
        ExcludeWithdrawals
    )

    serializer_class = WikiVersionSerializer

    required_read_scopes = [CoreScopes.WIKI_BASE_READ]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'wiki_versions'
    view_name = 'wiki-version-detail'

    # overrides RetrieveAPIView
    def get_object(self):
        return self.get_wiki_version()
