from framework.auth.core import Auth
from rest_framework import serializers as ser
from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import PermissionDenied, NotFound

from api.base.utils import token_creator
from api.base.utils import get_object_or_404
from api.nodes.serializers import NodeSerializer
from api.base.serializers import JSONAPISerializer
from website.project.model import DraftRegistration, Node
from api.draft_registrations.views import DraftRegistrationMixin




class RegistrationCreateSerializer(JSONAPISerializer):
    draft_id = ser.CharField(source='_id')
    warning_message = ser.CharField(read_only=True)

    class Meta:
        type_ = 'registrations'


class RegistrationCreateSerializerWithToken(NodeSerializer, DraftRegistrationMixin):
    draft_id = ser.CharField(write_only=True)
    id = ser.CharField(read_only=True, source='_id')
    title = ser.CharField(read_only=True)
    description = ser.CharField(read_only=True)
    category = ser.CharField(read_only=True)

    def validate(self, data):
        request = self.context['request']
        user = request.user
        if user.is_anonymous():
            raise PermissionDenied
        view = self.context['view']
        draft = get_object_or_404(DraftRegistration, data['draft_id'])
        if draft.is_deleted:
            raise NotFound(_('This resource has been deleted'))
        given_token = view.kwargs['token']
        correct_token = token_creator(draft._id, user._id)
        if correct_token != given_token:
            raise ser.ValidationError(_("Incorrect token."))
        return data

    def create(self, validated_data):
        request = self.context['request']
        draft = get_object_or_404(DraftRegistration, validated_data['draft_id'])
        node = draft.branched_from
        schema = draft.registration_schema
        data = draft.registration_metadata
        user = request.user
        registration = node.register_node(
            schema=schema,
            auth=Auth(user),
            template=schema.schema['title'],
            data=data
        )
        registration.is_deleted = False
        registration.registered_from = get_object_or_404(Node, node._id)
        registration.save()
        return registration
