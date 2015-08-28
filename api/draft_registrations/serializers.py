from rest_framework import serializers as ser
from dateutil.parser import parse as parse_date
from django.utils.translation import ugettext_lazy as _

from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError

from website.project.model import Q
from framework.auth.core import Auth
from api.base.exceptions import Gone
from api.base.utils import token_creator
from framework.exceptions import HTTPError
from api.base.utils import get_object_or_error
from api.base.serializers import JSONAPISerializer
from website.project.model import DraftRegistration
from website.project.views.drafts import get_schema_or_fail
from api.nodes.serializers import NodeSerializer, DraftRegistrationSerializer


class DraftRegSerializer(DraftRegistrationSerializer):
    def update(self, instance, validated_data):
        """
        Updates draft instance with the validated data.

        Requires the request to be in the serializer context.
        """

        schema_data = validated_data.get('registration_metadata')
        schema_name = validated_data.get('schema_name')
        schema_version = validated_data.get('schema_version', 1)
        if schema_name:
            try:
                meta_schema = get_schema_or_fail(
                    Q('name', 'eq', schema_name) &
                    Q('schema_version', 'eq', int(schema_version))
                )
                instance.registration_schema = meta_schema
            except HTTPError:
                raise NotFound(_("No schema record matching that query could be found"))

        if schema_data:
            instance.registration_metadata = schema_data
        instance.save()
        return instance

    class Meta:
        type_ = 'draft_registrations'


class RegistrationCreateSerializer(JSONAPISerializer):
    draft_id = ser.CharField(source='_id')
    warning_message = ser.CharField(read_only=True)

    class Meta:
        type_ = 'draft_registrations'


class RegistrationCreateSerializerWithToken(NodeSerializer):
    registration_choices = ['immediate', 'embargo']

    draft_id = ser.CharField(write_only=True)
    registration_choice = ser.ChoiceField(write_only=True, choices=registration_choices, help_text='Choose whether '
                        'to make your registration public immediately or embargo it for up to four years.')
    embargo_end_date = ser.DateField(write_only=True, required=False)
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
        draft = get_object_or_error(DraftRegistration, data['draft_id'])
        node = draft.branched_from
        if node.is_deleted:
            raise Gone(_('This resource has been deleted'))
        given_token = view.kwargs['token']
        correct_token = token_creator(draft._id, user._id)
        if correct_token != given_token:
            raise ser.ValidationError(_("Incorrect token."))
        return data

    def create(self, validated_data):
        """
        Second POST request for creating registration using new URL with token.
        """

        request = self.context['request']
        draft = get_object_or_error(DraftRegistration, validated_data['draft_id'])
        user = request.user
        registration = draft.register(auth=Auth(user))

        try:
            if validated_data.get('registration_choice', 'immediate') == 'embargo':
                embargo_end_date = validated_data.get('embargo_end_date')
                if embargo_end_date is None:
                    raise ValidationError(_('If embargo, must supply embargo end date.'))
                embargo_end_date = parse_date(embargo_end_date, ignoretz=True)
                registration.embargo_registration(user, embargo_end_date)
            else:
                registration.require_approval(user)
            registration.save()
        except ValueError as err:
                raise ValidationError(err.message)

        return registration
