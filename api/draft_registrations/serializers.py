from framework.auth.core import Auth
from rest_framework import serializers as ser
from dateutil.parser import parse as parse_date
from django.utils.translation import ugettext_lazy as _

from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError

from website import settings
from website.project.model import Q
from api.base.utils import token_creator
from api.base.utils import get_object_or_404
from api.base.serializers import JSONAPISerializer
from website.project.model import DraftRegistration
from website.project.views.drafts import get_schema_or_fail
from api.nodes.serializers import NodeSerializer, DraftRegistrationSerializer


class DraftRegSerializer(DraftRegistrationSerializer):
    def update(self, instance, validated_data):
        """Updates draft instance with the validated data. Requires
        the request to be in the serializer context.
        """

        schema_data = validated_data.get('registration_metadata')
        schema_name = validated_data.get('schema_name')
        schema_version = validated_data.get('schema_version', 1)
        if schema_name:
            meta_schema = get_schema_or_fail(
                Q('name', 'eq', schema_name) &
                Q('schema_version', 'eq', int(schema_version))
            )
            instance.registration_schema = meta_schema
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
    registration_choice = ser.ChoiceField(write_only=True, choices=registration_choices)
    embargo_end_date = ser.DateField(write_only=True, required=False)
    id = ser.CharField(read_only=True, source='_id')
    title = ser.CharField(read_only=True)
    description = ser.CharField(read_only=True)
    category = ser.CharField(read_only=True)

    def validate(self, data):
        """
        First POST request for creating a registration.

        User given a new URL with a token to confirm they want to register.

        """
        request = self.context['request']
        user = request.user
        if user.is_anonymous():
            raise PermissionDenied
        view = self.context['view']
        draft = get_object_or_404(DraftRegistration, data['draft_id'])
        node = draft.branched_from
        if node.is_deleted:
            raise NotFound(_('This resource has been deleted'))
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
        draft = get_object_or_404(DraftRegistration, validated_data['draft_id'])
        user = request.user
        registration = draft.register(auth=Auth(user))

        if validated_data.get('registration_choice', 'immediate') == 'embargo':
            embargo_end_date = validated_data.get('embargo_end_date')
            if embargo_end_date is None:
                raise ValidationError('If embargo, must supply embargo end date.')
            embargo_end_date = parse_date(embargo_end_date, ignoretz=True)
            try:
                registration.embargo_registration(user, embargo_end_date)
                registration.save()
            except ValueError as err:
                raise ValidationError({'message_long': err.message})
            if settings.ENABLE_ARCHIVER:
                # registration.archive_job.meta = {
                #     contrib._id: project_utils.get_embargo_urls(registration, contrib)
                #     for contrib in node.active_contributors()
                #
                # }
                registration.archive_job.save()

        else:
            registration.set_privacy('public', Auth(user), log=False)
            for child in registration.get_descendants_recursive(lambda n: n.primary):
                child.set_privacy('public', Auth(user), log=False)
        # TODO return Node or return "initiated" status and url's
        return registration
