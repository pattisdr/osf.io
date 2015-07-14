from framework.auth.core import Auth
from rest_framework import status
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.exceptions import NotAuthenticated
from django.utils.translation import ugettext_lazy as _
from rest_framework import generics, permissions as drf_permissions

from modularodm import Q
from api.base.filters import ODMFilterMixin
from api.nodes.views import NodeMixin
from website.models import DraftRegistration
from website.language import REGISTER_WARNING
from api.nodes.permissions import ContributorOrPublic
from api.draft_registrations.serializers import DraftRegSerializer, RegistrationCreateSerializer, RegistrationCreateSerializerWithToken
from api.base.utils import get_object_or_404, token_creator, absolute_reverse



class DraftRegistrationMixin(object):
    """Mixin with convenience methods for retrieving the current draft based on the
    current URL. By default, fetches the current draft based on the id kwarg.
    """

    serializer_class = DraftRegSerializer
    draft_lookup_url_kwarg = 'draft_id'

    def get_draft(self):
        obj = get_object_or_404(DraftRegistration, self.kwargs[self.draft_lookup_url_kwarg])
        # May raise a permission denied
        self.check_object_permissions(self.request, obj)
        return obj


class DraftRegistrationList(generics.ListCreateAPIView, ODMFilterMixin):
    """
    All draft registrations
    """

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
    )
    def get_serializer_class(self):
        if self.request.method == 'POST':
            serializer_class = RegistrationCreateSerializer
        else:
            serializer_class = DraftRegSerializer
        return serializer_class

    # overrides ListAPIView
    def get_queryset(self):
        user = self.request.user
        if user.is_anonymous():
            raise NotAuthenticated(_('Must be logged in to view draft registrations'))
        return DraftRegistration.find(Q('initiator', 'eq', user))

    # overrides ListCreateAPIView
    def create(self, request, *args):
        user = request.user
        draft = get_object_or_404(DraftRegistration, request.data['draft_id'])
        if draft.is_deleted:
            raise exceptions.NotFound(_('This resource has been deleted'))
        if user._id in draft.permissions.keys():
            if 'write' in draft.permissions[user._id]:
                token = token_creator(draft._id, user._id)
                url = absolute_reverse('draft_registrations:registration-create', kwargs={'token': token})
                registration_warning = REGISTER_WARNING.format((draft.title))
                return Response({'data': {'draft_id': draft._id, 'warning_message': registration_warning, 'links': {'confirm_register': url}}}, status=status.HTTP_202_ACCEPTED)
        raise exceptions.PermissionDenied


class DraftRegistrationDetail(generics.RetrieveUpdateDestroyAPIView, DraftRegistrationMixin):
    """
    Draft registration details
    """
    permission_classes = (
        ContributorOrPublic,
    )

    serializer_class = DraftRegSerializer

    # overrides RetrieveUpdateDestroyAPIView
    def get_object(self):
        draft = self.get_draft()
        return draft

    # overrides RetrieveUpdateDestroyAPIView
    def perform_destroy(self, instance):
        user = self.request.user
        auth = Auth(user)
        draft = self.get_object()
        draft.remove_node(auth=auth)
        draft.save()


class RegistrationCreateWithToken(generics.CreateAPIView, NodeMixin):
    """
    Freeze your registration draft
    """
    permission_classes = (
        ContributorOrPublic,
    )

    serializer_class = RegistrationCreateSerializerWithToken
