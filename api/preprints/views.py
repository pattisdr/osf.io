import re

from rest_framework import generics
from rest_framework.exceptions import NotFound, PermissionDenied, NotAuthenticated
from rest_framework import permissions as drf_permissions

from framework.auth.oauth_scopes import CoreScopes
from osf.models import ReviewAction, Preprint, PreprintContributor
from osf.utils.requests import check_select_for_update

from api.actions.permissions import ReviewActionPermission
from api.actions.serializers import ReviewActionSerializer
from api.actions.views import get_review_actions_queryset
from api.base.pagination import PreprintContributorPagination
from api.base.exceptions import Conflict
from api.base.views import JSONAPIBaseView, WaterButlerMixin
from api.base.filters import ListFilterMixin, PreprintFilterMixin
from api.base.parsers import (
    JSONAPIMultipleRelationshipsParser,
    JSONAPIMultipleRelationshipsParserForRegularJSON,
)
from api.base.utils import absolute_reverse, get_user_auth
from api.base import permissions as base_permissions
from api.citations.utils import render_citation
from api.preprints.serializers import (
    PreprintSerializer,
    PreprintCreateSerializer,
    PreprintCitationSerializer,
    PreprintContributorDetailSerializer,
    PreprintContributorsSerializer,
    PreprintStorageProviderSerializer,
    PreprintContributorsCreateSerializer
)
from api.files.serializers import OsfStorageFileSerializer
from api.nodes.serializers import (
    NodeCitationStyleSerializer,
)

from api.identifiers.views import IdentifierList
from api.identifiers.serializers import PreprintIdentifierSerializer
from api.nodes.views import NodeMixin, NodeContributorsList, NodeContributorDetail, NodeFilesList, NodeStorageProvidersList, NodeStorageProvider
from api.preprints.permissions import (
    PreprintPublishedOrAdmin,
    PreprintPublishedOrWrite,
    ModeratorIfNeverPublicWithdrawn,
    AdminOrPublic,
    ContributorDetailPermissions,
    PreprintFilesPermissions
)
from api.nodes.permissions import (
    ContributorOrPublic
)
from addons.osfstorage.models import OsfStorageFile
from api.requests.permissions import PreprintRequestPermission
from api.requests.serializers import PreprintRequestSerializer, PreprintRequestCreateSerializer
from api.requests.views import PreprintRequestMixin


class PreprintMixin(NodeMixin):
    serializer_class = PreprintSerializer
    preprint_lookup_url_kwarg = 'preprint_id'

    def get_preprint(self, check_object_permissions=True):
        qs = Preprint.objects.filter(guids___id=self.kwargs[self.preprint_lookup_url_kwarg], guids___id__isnull=False)
        try:
            preprint = qs.select_for_update().get() if check_select_for_update(self.request) else qs.select_related('node').get()
        except Preprint.DoesNotExist:
            raise NotFound

        if preprint.deleted is not None:
            raise NotFound

        # May raise a permission denied
        if check_object_permissions:
            self.check_object_permissions(self.request, preprint)

        return preprint


class PreprintList(JSONAPIBaseView, generics.ListCreateAPIView, PreprintFilterMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/preprints_list).
    """
    # These permissions are not checked for the list of preprints, permissions handled by the query
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ContributorOrPublic,
    )

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)

    required_read_scopes = [CoreScopes.PREPRINTS_READ]
    required_write_scopes = [CoreScopes.PREPRINTS_WRITE]

    serializer_class = PreprintSerializer

    ordering = ('-created')
    ordering_fields = ('created', 'date_last_transitioned')
    view_category = 'preprints'
    view_name = 'preprint-list'

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PreprintCreateSerializer
        else:
            return PreprintSerializer

    def get_default_queryset(self):
        auth = get_user_auth(self.request)
        auth_user = getattr(auth, 'user', None)

        # Permissions on the list objects are handled by the query
        return self.preprints_queryset(Preprint.objects.all(), auth_user)

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()


class PreprintDetail(JSONAPIBaseView, generics.RetrieveUpdateAPIView, PreprintMixin, WaterButlerMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/preprints_read).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ModeratorIfNeverPublicWithdrawn,
        ContributorOrPublic,
        PreprintPublishedOrWrite,
    )
    parser_classes = (
        JSONAPIMultipleRelationshipsParser,
        JSONAPIMultipleRelationshipsParserForRegularJSON,
    )

    required_read_scopes = [CoreScopes.PREPRINTS_READ]
    required_write_scopes = [CoreScopes.PREPRINTS_WRITE]

    serializer_class = PreprintSerializer

    view_category = 'preprints'
    view_name = 'preprint-detail'

    def get_object(self):
        return self.get_preprint()

    def get_parser_context(self, http_request):
        """
        Tells parser that type is required in request
        """
        res = super(PreprintDetail, self).get_parser_context(http_request)
        res['legacy_type_allowed'] = True
        return res


class PreprintCitationDetail(JSONAPIBaseView, generics.RetrieveAPIView, PreprintMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/preprints_citation_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.PREPRINT_CITATIONS_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = PreprintCitationSerializer
    view_category = 'preprints'
    view_name = 'preprint-citation'

    def get_object(self):
        preprint = self.get_preprint()
        auth = get_user_auth(self.request)

        if preprint.can_view(auth):
            return preprint.csl

        raise PermissionDenied if auth.user else NotAuthenticated


class PreprintCitationStyleDetail(JSONAPIBaseView, generics.RetrieveAPIView, PreprintMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/preprints_citation_read).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.PREPRINT_CITATIONS_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = NodeCitationStyleSerializer
    view_category = 'preprint'
    view_name = 'preprint-citation'

    def get_object(self):
        preprint = self.get_preprint()
        auth = get_user_auth(self.request)
        style = self.kwargs.get('style_id')

        if preprint.can_view(auth):
            try:
                citation = render_citation(node=preprint, style=style)
            except ValueError as err:  # style requested could not be found
                csl_name = re.findall('[a-zA-Z]+\.csl', err.message)[0]
                raise NotFound('{} is not a known style.'.format(csl_name))

            return {'citation': citation, 'id': style}

        raise PermissionDenied if auth.user else NotAuthenticated


class PreprintIdentifierList(IdentifierList, PreprintMixin):
    """List of identifiers for a specified preprint. *Read-only*.

    ##Identifier Attributes

    OSF Identifier entities have the "identifiers" `type`.

        name           type                   description
        ----------------------------------------------------------------------------
        category       string                 e.g. 'ark', 'doi'
        value          string                 the identifier value itself

    ##Links

        self: this identifier's detail page

    ##Relationships

    ###Referent

    The identifier is refers to this preprint.

    ##Actions

    *None*.

    ##Query Params

     Identifiers may be filtered by their category.

    #This Request/Response

    """

    permission_classes = (
        PreprintPublishedOrAdmin,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )
    serializer_class = PreprintIdentifierSerializer
    required_read_scopes = [CoreScopes.IDENTIFIERS_READ]
    required_write_scopes = [CoreScopes.NULL]

    preprint_lookup_url_kwarg = 'preprint_id'

    view_category = 'preprints'
    view_name = 'identifier-list'

    # overrides IdentifierList
    def get_object(self, check_object_permissions=True):
        return self.get_preprint(check_object_permissions=check_object_permissions)


class PreprintContributorsList(NodeContributorsList, PreprintMixin):
    permission_classes = (
        AdminOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        PreprintPublishedOrAdmin,
    )

    pagination_class = PreprintContributorPagination

    required_read_scopes = [CoreScopes.PREPRINT_CONTRIBUTORS_READ]
    required_write_scopes = [CoreScopes.PREPRINT_CONTRIBUTORS_WRITE]

    view_category = 'preprints'
    view_name = 'preprint-contributors'
    serializer_class = PreprintContributorsSerializer

    def get_default_queryset(self):
        preprint = self.get_preprint()
        return preprint.preprintcontributor_set.all().include('user__guids')

    # overrides NodeContributorsList
    def get_serializer_class(self):
        """
        Use NodeContributorDetailSerializer which requires 'id'
        """
        if self.request.method == 'PUT' or self.request.method == 'PATCH' or self.request.method == 'DELETE':
            return PreprintContributorDetailSerializer
        elif self.request.method == 'POST':
            return PreprintContributorsCreateSerializer
        else:
            return PreprintContributorsSerializer

    def get_resource(self):
        return self.get_preprint()

    # Overrides NodeContributorsList
    def get_serializer_context(self):
        context = JSONAPIBaseView.get_serializer_context(self)
        context['resource'] = self.get_resource()
        context['default_email'] = 'preprint'
        return context


class PreprintContributorDetail(NodeContributorDetail, PreprintMixin):

    permission_classes = (
        ContributorDetailPermissions,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    view_category = 'preprints'
    view_name = 'preprint-contributor-detail'
    serializer_class = PreprintContributorDetailSerializer

    required_read_scopes = [CoreScopes.PREPRINT_CONTRIBUTORS_READ]
    required_write_scopes = [CoreScopes.PREPRINT_CONTRIBUTORS_WRITE]

    def get_resource(self):
        return self.get_preprint()

    # overrides RetrieveAPIView
    def get_object(self):
        preprint = self.get_preprint()
        user = self.get_user()
        # May raise a permission denied
        self.check_object_permissions(self.request, user)
        try:
            return preprint.preprintcontributor_set.get(user=user)
        except PreprintContributor.DoesNotExist:
            raise NotFound('{} cannot be found in the list of contributors.'.format(user))

    def get_serializer_context(self):
        context = JSONAPIBaseView.get_serializer_context(self)
        context['resource'] = self.get_preprint()
        context['default_email'] = 'preprint'
        return context


class PreprintActionList(JSONAPIBaseView, generics.ListCreateAPIView, ListFilterMixin, PreprintMixin):
    """Action List *Read-only*

    Actions represent state changes and/or comments on a reviewable object (e.g. a preprint)

    ##Action Attributes

        name                            type                                description
        ====================================================================================
        date_created                    iso8601 timestamp                   timestamp that the action was created
        date_modified                   iso8601 timestamp                   timestamp that the action was last modified
        from_state                      string                              state of the reviewable before this action was created
        to_state                        string                              state of the reviewable after this action was created
        comment                         string                              comment explaining the state change
        trigger                         string                              name of the trigger for this action

    ##Relationships

    ###Target
    Link to the object (e.g. preprint) this action acts on

    ###Provider
    Link to detail for the target object's provider

    ###Creator
    Link to the user that created this action

    ##Links
    - `self` -- Detail page for the current action

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    Actions may be filtered by their `id`, `from_state`, `to_state`, `date_created`, `date_modified`, `creator`, `provider`, `target`
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ReviewActionPermission,
    )

    required_read_scopes = [CoreScopes.ACTIONS_READ]
    required_write_scopes = [CoreScopes.ACTIONS_WRITE]

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)
    serializer_class = ReviewActionSerializer
    model_class = ReviewAction

    ordering = ('-created',)
    view_category = 'preprints'
    view_name = 'preprint-review-action-list'

    # overrides ListCreateAPIView
    def perform_create(self, serializer):
        target = serializer.validated_data['target']
        self.check_object_permissions(self.request, target)

        if not target.provider.is_reviewed:
            raise Conflict('{} is an unmoderated provider. If you are an admin, set up moderation by setting `reviews_workflow` at {}'.format(
                target.provider.name,
                absolute_reverse('providers:preprint-providers:preprint-provider-detail', kwargs={
                    'provider_id': target.provider._id,
                    'version': self.request.parser_context['kwargs']['version']
                })
            ))

        serializer.save(user=self.request.user)

    # overrides ListFilterMixin
    def get_default_queryset(self):
        return get_review_actions_queryset().filter(target_id=self.get_preprint().id)

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()


class PreprintStorageProvidersList(NodeStorageProvidersList, PreprintMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        base_permissions.TokenHasScope,
        PreprintFilesPermissions,
    )

    required_read_scopes = [CoreScopes.PREPRINT_FILE_READ]
    required_write_scopes = [CoreScopes.PREPRINT_FILE_WRITE]

    serializer_class = PreprintStorageProviderSerializer
    view_category = 'preprints'
    view_name = 'preprint-storage-providers'

    def get_provider_item(self, provider):
        return NodeStorageProvider(provider, self.get_preprint())

    def get_queryset(self):
        # Preprints Providers restricted so only osfstorage is allowed
        return [
            self.get_provider_item('osfstorage')
        ]


class PreprintFilesList(NodeFilesList, PreprintMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        PreprintFilesPermissions,
    )
    required_read_scopes = [CoreScopes.PREPRINT_FILE_READ]
    required_write_scopes = [CoreScopes.PREPRINT_FILE_WRITE]

    view_category = 'preprints'
    view_name = 'preprint-files'

    serializer_class = OsfStorageFileSerializer

    def get_queryset(self):
        # Restricting queryset so only primary file is returned.
        preprint = self.get_preprint()
        return OsfStorageFile.objects.filter(id=getattr(preprint.primary_file, 'id', None))


class PreprintRequestListCreate(JSONAPIBaseView, generics.ListCreateAPIView, ListFilterMixin, PreprintRequestMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        PreprintRequestPermission
    )

    required_read_scopes = [CoreScopes.PREPRINT_REQUESTS_READ]
    required_write_scopes = [CoreScopes.PREPRINT_REQUESTS_WRITE]

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)

    serializer_class = PreprintRequestSerializer

    view_category = 'preprint-requests'
    view_name = 'preprint-request-list'

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PreprintRequestCreateSerializer
        else:
            return PreprintRequestSerializer

    def get_default_queryset(self):
        return self.get_target().requests.all()

    def get_queryset(self):
        return self.get_queryset_from_request()
