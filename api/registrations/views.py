from rest_framework import status
from rest_framework import generics
from rest_framework import exceptions
from rest_framework.response import Response
from django.utils.translation import ugettext_lazy as _

from modularodm import Q
from api.base.utils import get_object_or_404
from website.language import REGISTER_WARNING
from api.nodes.views import NodeList, NodeMixin
from api.nodes.serializers import NodeSerializer
from api.base.utils import token_creator, absolute_reverse
from api.draft_registrations.views import DraftRegistration
from api.draft_registrations.permissions import ContributorOrPublic
from api.registrations.serializers import RegistrationCreateSerializer, RegistrationCreateSerializerWithToken


class RegistrationList(NodeList):
    """Node registrations"""

    permission_classes = (
        ContributorOrPublic,
    )

    def get_serializer_class(self):
        if self.request.method == 'POST':
            serializer_class = RegistrationCreateSerializer
        else:
            serializer_class = NodeSerializer
        return serializer_class

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        base_query = (
            Q('is_deleted', 'ne', True) &
            Q('is_folder', 'ne', True) &
            (Q('is_registration', 'eq', True))
        )
        user = self.request.user
        permission_query = Q('is_public', 'eq', True)
        if not user.is_anonymous():
            permission_query = (Q('is_public', 'eq', True) | Q('contributors', 'icontains', user._id))
        query = base_query & permission_query
        return query

    # overrides ListCreateAPIView
    def create(self, request, *args):
        user = request.user
        draft = get_object_or_404(DraftRegistration, request.data['draft_id'])
        if draft.is_deleted:
            raise exceptions.NotFound(_('This resource has been deleted'))
        self.check_object_permissions(self.request, draft)
        token = token_creator(draft._id, user._id)
        url = absolute_reverse('registrations:registration-create', kwargs={'token': token})
        registration_warning = REGISTER_WARNING.format((draft.title))
        return Response({'data': {'draft_id': draft._id, 'warning_message': registration_warning, 'links': {'confirm_register': url}}}, status=status.HTTP_202_ACCEPTED)


class RegistrationCreateWithToken(generics.CreateAPIView, NodeMixin):
    """
    Freeze your registration draft
    """
    permission_classes = (
        ContributorOrPublic,
    )

    serializer_class = RegistrationCreateSerializerWithToken


