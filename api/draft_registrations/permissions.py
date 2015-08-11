from framework.auth import Auth
from rest_framework import permissions

from website.models import Node, Pointer, DraftRegistration

def get_user_auth(request):
    user = request.user
    if user.is_anonymous():
        auth = Auth(None)
    else:
        auth = Auth(user)
    return auth


class ContributorOrPublic(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, (DraftRegistration)), 'obj must be a DraftRegistration, got {}'.format(obj)
        node = obj.branched_from
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return node.is_public or node.can_view(auth)
        else:
            return node.can_edit(auth)
