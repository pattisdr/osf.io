from rest_framework import generics, permissions as drf_permissions
from modularodm import Q

from api.base.utils import get_registration_or_404
from website.models import Node
from api.base.filters import ODMFilterMixin
from api.registrations.serializers import RegistrationSerializer
from api.nodes.serializers import NodePointersSerializer
from api.nodes.views import NodeMixin, NodeFilesList, NodeChildrenList, NodeContributorsList

from api.nodes.permissions import ContributorOrPublic, ReadOnlyIfRegistration

class RegistrationMixin(NodeMixin):
    """Mixin with convenience methods for retrieving the current node based on the
    current URL. By default, fetches the current node based on the pk kwarg.
    """

    serializer_class = RegistrationSerializer
    node_lookup_url_kwarg = 'registration_id'

    def get_registration(self):
        obj = get_registration_or_404(Node, self.kwargs[self.node_lookup_url_kwarg])
        # May raise a permission denied
        self.check_object_permissions(self.request, obj)
        return obj

class RegistrationList(generics.ListAPIView, ODMFilterMixin):
    """All node registrations"""

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
    )
    serializer_class = RegistrationSerializer

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        base_query = (
            Q('is_deleted', 'ne', True) &
            Q('is_folder', 'ne', True) &
            (Q('is_registration', 'eq', True) | Q('is_registration_draft', 'eq', True))
        )
        user = self.request.user
        permission_query = Q('is_public', 'eq', True)
        if not user.is_anonymous():
            permission_query = (Q('is_public', 'eq', True) | Q('contributors', 'icontains', user._id))

        query = base_query & permission_query
        return query

    # overrides ListCreateAPIView
    def get_queryset(self):
        query = self.get_query_from_request()
        return Node.find(query)


class RegistrationDetail(generics.RetrieveAPIView, RegistrationMixin):
    """
    Registration details
    """
    permission_classes = (
        ContributorOrPublic,
        ReadOnlyIfRegistration,
    )
    serializer_class = RegistrationSerializer

    # overrides RetrieveAPIView
    def get_object(self):
        return self.get_registration()


class RegistrationContributorsList(NodeContributorsList, RegistrationMixin):
    """
    Contributors(users) for a registration
    """

class RegistrationChildrenList(NodeChildrenList, RegistrationMixin):
    """
    Children of the current registration
    """


class RegistrationPointersList(generics.ListAPIView, RegistrationMixin):
    """
    Registration pointers
    """

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
    )

    serializer_class = NodePointersSerializer

    def get_queryset(self):
        pointers = self.get_registration().nodes_pointer
        return pointers


class RegistrationFilesList(NodeFilesList, RegistrationMixin):
    """
    Files attached to a registration
    """
