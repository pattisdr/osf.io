from rest_framework import serializers as ser, exceptions

from framework.auth.core import Auth
from api.base.serializers import (
    IDField,
    LinksField,
    JSONAPISerializer,
    RelationshipField,
    TypeField,
    VersionedDateTimeField,
)
from api.base.utils import absolute_reverse
from api.nodes.serializers import CompoundIDField
from osf.models import OSFUser
from osf.models.osf_group import OSFGroup
from osf.utils.permissions import GROUP_MEMBER_PERMISSIONS, MEMBER, MANAGER


class OSFGroupSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'name',
    ])

    id = IDField(source='_id', read_only=True)
    type = TypeField()
    name = ser.CharField(required=True)
    date_created = VersionedDateTimeField(source='created', read_only=True)
    date_modified = VersionedDateTimeField(source='modified', read_only=True)

    links = LinksField({
        'self': 'get_absolute_url',
    })

    def get_absolute_url(self, obj):
        return obj.get_absolute_url()

    members = RelationshipField(
        related_view='osf_groups:group-members',
        related_view_kwargs={'group_id': '<_id>'},
    )

    class Meta:
        type_ = 'osf_groups'

    def create(self, validated_data):
        group = OSFGroup(creator=validated_data['creator'], name=validated_data['name'])
        group.save()
        return group

    def update(self, instance, validated_data):
        if 'name' in validated_data:
            instance.set_group_name(validated_data.get('name'))
            instance.save()
        return instance


class OSFGroupDetailSerializer(OSFGroupSerializer):
    """
    Overrides OSFGroupSerializer to make id required.
    """
    id = IDField(source='_id', required=True)


class GroupCompoundIDField(CompoundIDField):
    def _get_resource_id(self):
        return self.context['request'].parser_context['kwargs']['group_id']


class OSFGroupMemberSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'role',
        'full_name',
    ])
    writeable_method_fields = frozenset([
        'role',
    ])
    id = GroupCompoundIDField(source='_id', read_only=True)
    type = TypeField()
    role = ser.SerializerMethodField()
    unregistered_member = ser.SerializerMethodField()
    full_name = ser.CharField(read_only=True, source='fullname')

    users = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<_id>'},
    )

    links = LinksField({
        'self': 'get_absolute_url',
    })

    def get_role(self, user):
        return user.group_role(self.context['group'])

    def get_unregistered_member(self, obj):
        unclaimed_records = obj.unclaimed_records.get(self.context['group']._id, None)
        if unclaimed_records:
            return unclaimed_records.get('name', None)

    def get_member_method(self, group, role):
        methods = {
            MANAGER: group.make_manager,
            MEMBER: group.make_member,
        }
        return methods[role]

    def get_group_role(self, validated_data, default_role):
        role = validated_data.get('role', default_role)
        if role not in GROUP_MEMBER_PERMISSIONS:
            raise exceptions.ValidationError('{} is not a valid role; choose manager or member.'.format(role))
        return role

    class Meta:
        type_ = 'group_members'

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'osf_groups:group-member-detail',
            kwargs={
                'user_id': obj._id,
                'group_id': self.context['request'].parser_context['kwargs']['group_id'],
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )


class OSFGroupMemberCreateSerializer(OSFGroupMemberSerializer):
    id = GroupCompoundIDField(source='_id', required=False, allow_null=True)
    type = TypeField()
    full_name = ser.CharField(required=False)
    email = ser.EmailField(required=False, write_only=True)

    def get_user_object(self, user_id, group):
        if user_id:
            user = OSFUser.load(user_id)
            if not user:
                raise exceptions.NotFound(detail='User with id {} not found.'.format(user_id))
            if group.has_permission(user, 'member'):
                raise exceptions.ValidationError(detail='User is already a member of this group.')
            return user
        return user_id

    def create(self, validated_data):
        group = self.context['group']
        user = self.get_user_object(validated_data.get('_id', None), group)
        auth = Auth(self.context['request'].user)
        full_name = validated_data.get('full_name', None)
        email = validated_data.get('email', None)
        role = self.get_group_role(validated_data, MEMBER)

        try:
            # Making someone a member has the potential to violate the one-manager rule
            # (This either adds a new user as a member or downgrades a manager to a member)
            if user:
                self.get_member_method(group, role)(user, auth)
            else:
                if not full_name or not email:
                    raise exceptions.ValidationError(detail='You must provide a full_name/email combination to add an unconfirmed member.')
                else:
                    user = group.add_unregistered_member(full_name, email, auth, role)
        except ValueError as e:
            raise exceptions.ValidationError(detail=e)

        return user

    class Meta:
        type_ = 'group_members'


class OSFGroupMemberDetailSerializer(OSFGroupMemberSerializer):
    id = GroupCompoundIDField(source='_id', required=True)

    def update(self, user, validated_data):
        group = self.context['group']
        role = self.get_group_role(validated_data, user.group_role(group))
        auth = Auth(self.context['request'].user)

        try:
            # Making sure the one-manager rule isn't violated
            self.get_member_method(self.context['group'], role)(user, auth)
        except ValueError as e:
            raise exceptions.ValidationError(detail=e)

        return user