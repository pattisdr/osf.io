from django.apps import apps
from django.db.models import Q

from rest_framework import generics, permissions as drf_permissions, exceptions
from rest_framework.exceptions import NotFound, ValidationError
from guardian.shortcuts import get_perms

from api.base import permissions as base_permissions
from api.base.exceptions import InvalidFilterOperator, InvalidFilterValue
from api.base.filters import ListFilterMixin
from api.base.utils import get_object_or_error, get_user_auth, is_bulk_request
from api.base.views import JSONAPIBaseView
from api.base import generic_bulk_views as bulk_views
from api.base.parsers import JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON
from api.osf_groups.permissions import IsGroupManager
from api.osf_groups.serializers import (
    OSFGroupSerializer,
    OSFGroupDetailSerializer,
    OSFGroupMemberSerializer,
    OSFGroupMemberDetailSerializer,
    OSFGroupMemberCreateSerializer,
)
from api.users.views import UserMixin
from framework.auth.oauth_scopes import CoreScopes
from osf.models import OSFGroup, OSFUser
from osf.utils.permissions import MANAGER, MEMBER, GROUP_MEMBER_PERMISSIONS


class OSFGroupMixin(object):
    """
    Mixin with convenience method for retrieving the current OSF Group
    """
    group_lookup_url_kwarg = 'group_id'

    def get_osf_group(self, check_object_permissions=True):

        group = get_object_or_error(
            OSFGroup,
            self.kwargs[self.group_lookup_url_kwarg],
            self.request,
            display_name='osf_group',
        )

        if check_object_permissions:
            self.check_object_permissions(self.request, group)
        return group

    def get_node_group_perms(self, group, node):
        return get_perms(group.member_group, node)


class OSFGroupList(JSONAPIBaseView, generics.ListCreateAPIView, ListFilterMixin, OSFGroupMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.OSF_GROUPS_READ]
    required_write_scopes = [CoreScopes.OSF_GROUPS_WRITE]
    model_class = apps.get_model('osf.OSFGroup')

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)
    serializer_class = OSFGroupSerializer
    view_category = 'osf_groups'
    view_name = 'group-list'
    ordering = ('-modified', )

    def get_default_queryset(self):
        return OSFGroup.objects.all()

    # overrides ListCreateAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()

    # overrides ListCreateAPIView
    def perform_create(self, serializer):
        """Create an OSFGroup.

        :param serializer:
        """
        # On creation, logged in user is the creator
        user = self.request.user
        serializer.save(creator=user)


class OSFGroupDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, OSFGroupMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        IsGroupManager,
    )
    required_read_scopes = [CoreScopes.OSF_GROUPS_READ]
    required_write_scopes = [CoreScopes.OSF_GROUPS_WRITE]
    model_class = apps.get_model('osf.OSFGroup')

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)
    serializer_class = OSFGroupDetailSerializer
    view_category = 'osf_groups'
    view_name = 'group-detail'
    ordering = ('-modified', )

    # Overrides RetrieveUpdateDestroyAPIView
    def get_object(self):
        return self.get_osf_group()

    # Overrides RetrieveUpdateDestroyAPIView
    def perform_destroy(self, instance):
        auth = get_user_auth(self.request)
        instance.remove_group(auth=auth)


class OSFGroupMemberBaseView(JSONAPIBaseView, OSFGroupMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        IsGroupManager,
    )
    required_read_scopes = [CoreScopes.OSF_GROUPS_READ]
    required_write_scopes = [CoreScopes.OSF_GROUPS_WRITE]

    model_class = apps.get_model('osf.OSFUser')
    serializer_class = OSFGroupMemberSerializer
    view_category = 'osf_groups'
    ordering = ('-modified', )

    def _assert_member_belongs_to_group(self, user):
        group = self.get_osf_group()
        # Checking group membership instead of permissions, so unregistered members are
        # recognized as group members
        if not group.is_member(user):
            raise NotFound('{} cannot be found in this OSFGroup'.format(user._id))

    def get_serializer_class(self):
        if self.request.method == 'PUT' or self.request.method == 'PATCH' or self.request.method == 'DELETE':
            return OSFGroupMemberDetailSerializer
        elif self.request.method == 'POST':
            return OSFGroupMemberCreateSerializer
        else:
            return OSFGroupMemberSerializer

    # overrides DestroyAPIView
    def perform_destroy(self, instance):
        group = self.get_osf_group()
        auth = get_user_auth(self.request)
        methods = {
            MANAGER: group.remove_manager,
            MEMBER: group.remove_member,
        }
        try:
            methods[instance.group_role(group)](instance, auth)
        except ValueError as e:
            raise exceptions.ValidationError(detail=e)


class OSFGroupMembersList(OSFGroupMemberBaseView, bulk_views.BulkUpdateJSONAPIView, bulk_views.BulkDestroyJSONAPIView, bulk_views.ListBulkCreateJSONAPIView, ListFilterMixin):
    view_name = 'group-members'

    # Overrides ListAPIView
    def get_queryset(self):
        queryset = self.get_queryset_from_request()
        if is_bulk_request(self.request):
            user_ids = []
            for user in self.request.data:
                try:
                    user_ids.append(user['id'].split('-')[1])
                except AttributeError:
                    raise ValidationError('Member identifier not provided.')
                except IndexError:
                    raise ValidationError('Member identifier incorrectly formatted')
            queryset = queryset.filter(guids___id__in=user_ids)
        return queryset

    def get_default_queryset(self):
        return self.get_osf_group().members

    def get_serializer_context(self):
        context = super(OSFGroupMembersList, self).get_serializer_context()
        context['group'] = self.get_osf_group()
        return context

    # Overrides BulkDestroyJSONAPIView
    def get_requested_resources(self, request, request_data):
        requested_ids = []
        for data in request_data:
            try:
                requested_ids.append(data['id'].split('-')[1])
            except IndexError:
                raise ValidationError('Contributor identifier incorrectly formatted.')

        resource_object_list = OSFUser.objects.filter(guids___id__in=requested_ids)
        for resource in resource_object_list:
            self._assert_member_belongs_to_group(resource)

        if len(resource_object_list) != len(request_data):
            raise ValidationError({'non_field_errors': 'Could not find all objects to delete.'})

        return resource_object_list

    def build_query_from_field(self, field_name, operation):
        if field_name == 'role':
            group = self.get_osf_group(check_object_permissions=False)
            if operation['op'] != 'eq':
                raise InvalidFilterOperator(value=operation['op'], valid_operators=['eq'])
            # operation['value'] should be 'member' or 'manager'
            query_val = operation['value'].lower().strip()
            if query_val not in GROUP_MEMBER_PERMISSIONS:
                raise InvalidFilterValue(value=operation['value'])
            return Q(id__in=group.managers if query_val == MANAGER else group.members_only)
        return super(OSFGroupMembersList, self).build_query_from_field(field_name, operation)


class OSFGroupMemberDetail(OSFGroupMemberBaseView, generics.RetrieveUpdateDestroyAPIView, UserMixin):
    view_name = 'group-member-detail'

    def get_object(self):
        user = self.get_user()
        self.check_object_permissions(self.request, user)
        self._assert_member_belongs_to_group(user)
        return user

    def get_serializer_context(self):
        context = super(OSFGroupMemberDetail, self).get_serializer_context()
        context['group'] = self.get_osf_group()
        return context