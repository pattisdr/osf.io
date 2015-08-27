import datetime
from dateutil.relativedelta import relativedelta
from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase, fake
from api.base.utils import token_creator
from api.base.settings.defaults import API_BASE
from website.project.model import ensure_schemas
from tests.factories import UserFactory, ProjectFactory, RegistrationFactory, DraftRegistrationFactory


class TestDraftRegistrationList(ApiTestCase):
    def setUp(self):
        ensure_schemas()
        super(TestDraftRegistrationList, self).setUp()
        self.user = UserFactory.build()
        password = fake.password()
        self.password = password
        self.user.set_password(password)
        self.user.save()
        self.basic_auth = (self.user.username, password)

        self.user_two = UserFactory.build()
        self.user_two.set_password(password)
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, password)

        self.public_project = ProjectFactory(creator=self.user, is_public=True)
        self.public_draft = DraftRegistrationFactory(branched_from=self.public_project, initiator=self.user)
        self.registration = RegistrationFactory(source=self.public_project, creator=self.user)

        self.private_project = ProjectFactory(creator=self.user, is_public=False)
        self.private_draft = DraftRegistrationFactory(branched_from=self.private_project, initiator=self.user)

        self.url = '/{}draft_registrations/'.format(API_BASE)

    def test_return_draft_registration_list_logged_out(self):
        res = self.app.get(self.url, expect_errors=True)
        # 403 until my changes are merged in
        assert_equal(res.status_code, 403)

    def test_return_draft_registration_list_logged_in_contributor(self):
        res = self.app.get(self.url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 2)

    def test_return_draft_registration_list_logged_in_non_contributor(self):
        res = self.app.get(self.url, auth=self.basic_auth_two)
        assert_equal(len(res.json['data']), 0)
        assert_equal(res.status_code, 200)

    def test_draft_list_omits_drafts_that_have_been_made_into_registrations(self):
        self.public_draft.registered_node = self.registration
        self.public_draft.save()
        res = self.app.get(self.url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)


class TestRegistrationCreate(ApiTestCase):
    def setUp(self):
        ensure_schemas()
        super(TestRegistrationCreate, self).setUp()
        self.user = UserFactory.build()
        password = fake.password()
        self.password = password
        self.user.set_password(password)
        self.user.save()
        self.basic_auth = (self.user.username, password)

        self.user_two = UserFactory.build()
        self.user_two.set_password(password)
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, password)

        self.public_project = ProjectFactory(creator=self.user, is_public=True)
        self.public_draft = DraftRegistrationFactory(initiator=self.user, branched_from=self.public_project)
        self.public_url = '/{}draft_registrations/'.format(API_BASE)
        self.public_payload_immediate = {'draft_id': self.public_draft._id, 'registration_choice': 'immediate'}
        today = datetime.date.today()
        end_date = today + relativedelta(years=1)
        self.embargo_payload = {'draft_id': self.public_draft._id, 'registration_choice': 'embargo', 'embargo_end_date': end_date}

        self.private_project = ProjectFactory(creator=self.user, is_private=True)
        self.private_draft = DraftRegistrationFactory(initiator=self.user, branched_from=self.private_project)
        self.private_url = '/{}draft_registrations/'.format(API_BASE)
        self.private_payload_immediate = {'draft_id': self.private_draft._id, 'registration_choice': 'immediate'}


        self.registration = RegistrationFactory(project=self.public_project)

    def test_create_registration_from_node(self):
        url = '/{}draft_registrations/'.format(API_BASE)
        res = self.app.post(url, {'draft_id': self.public_project._id, 'registration_choice': 'immediate'}, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_create_registration_from_registration(self):
        url = '/{}draft_registrations/'.format(API_BASE)
        res = self.app.post(url, {'draft_id':  self.registration._id, 'registration_choice': 'immediate'}, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_create_registration_where_source_has_been_deleted(self):
        project = ProjectFactory(creator=self.user, is_public=True)
        draft = DraftRegistrationFactory(branched_from=project, initiator=self.user)
        project.is_deleted = True
        project.save()
        url = '/{}draft_registrations/'.format(API_BASE)
        res = self.app.post(url, {'draft_id': draft._id, 'registration_choice': 'immediate'}, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_equal(res.json['errors'][0]['detail'], 'Source has been deleted.')

        res = self.app.post(url, {'draft_id':  self.registration._id, 'registration_choice': 'immediate'}, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_create_public_registration_logged_out(self):
        res = self.app.post(self.public_url, self.public_payload_immediate, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_create_public_registration_logged_in(self):
        res = self.app.post(self.public_url, self.public_payload_immediate, auth=self.basic_auth, expect_errors=True)
        token_url = res.json['links']['confirm_register']
        assert_equal(res.status_code, 202)

        res = self.app.post(token_url, self.public_payload_immediate, auth=self.basic_auth, expect_errors = True)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['title'], self.public_project.title)
        assert_equal(res.json['data']['attributes']['properties']['registration'], True)
        assert_equal(res.json['data']['attributes']['public'], True)


    def test_create_registration_from_deleted_draft(self):
        url = '/{}draft_registrations/{}/'.format(API_BASE, self.public_draft._id)
        res = self.app.delete(url, auth=self.basic_auth)
        assert_equal(res.status_code, 204)
        res = self.app.post(self.public_url, self.public_payload_immediate, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_create_registration_with_token_from_deleted_draft(self):
        url = '/{}draft_registrations/{}/'.format(API_BASE, self.public_draft._id)
        res = self.app.delete(url, auth=self.basic_auth)
        assert_equal(res.status_code, 204)
        token = token_creator(self.public_draft._id, self.user._id)
        url = '/{}draft_registrations/freeze/{}/'.format(API_BASE, token)
        res = self.app.post(url, self.public_payload_immediate, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_invalid_token_create_registration(self):
        res = self.app.post(self.private_url, self.private_payload_immediate, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 202)
        token_url = self.private_url + "freeze/12345/"

        res = self.app.post(token_url, self.private_payload_immediate, auth=self.basic_auth, expect_errors = True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail']['non_field_errors'][0], "Incorrect token.")

    def test_create_private_registration_logged_out(self):
        res = self.app.post(self.private_url, self.private_payload_immediate, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_create_public_registration_logged_out_with_token(self):
        token = token_creator(self.public_draft._id, self.user._id)
        url = '/{}draft_registrations/freeze/{}/'.format(API_BASE, token)
        res = self.app.post(url, self.public_payload_immediate, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_create_private_registration_logged_out_with_token(self):
        token = token_creator(self.private_draft._id, self.user._id)
        url = '/{}draft_registrations/freeze/{}/'.format(API_BASE, token)
        res = self.app.post(url, self.private_payload_immediate, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_create_private_registration_logged_in_contributor(self):
        res = self.app.post(self.private_url, self.private_payload_immediate, auth=self.basic_auth, expect_errors=True)
        token_url = res.json['links']['confirm_register']
        assert_equal(res.status_code, 202)

        res = self.app.post(token_url, self.private_payload_immediate, auth=self.basic_auth, expect_errors = True)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['title'], self.private_project.title)
        assert_equal(res.json['data']['attributes']['properties']['registration'], True)
        assert_equal(res.json['data']['attributes']['public'], True)

        url = self.private_url + 'self.private_draft._id/'
        res = self.app.get(url, self.private_payload_immediate, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_create_private_registration_logged_in_non_contributor(self):
        res = self.app.post(self.private_url, self.private_payload_immediate, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_create_private_registration_logged_in_read_only_contributor(self):
        self.private_project.add_contributor(self.user_two, permissions=['read'])
        self.private_project.save()
        draft = DraftRegistrationFactory(initiator=self.user, branched_from=self.private_project)
        res = self.app.post(self.private_url, {'draft_id': draft._id, 'registration_choice': 'immediate'}, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_embargo_date_required_if_embargo_specified(self):
        token = token_creator(self.public_draft._id, self.user._id)
        url = '/{}draft_registrations/freeze/{}/'.format(API_BASE, token)
        res = self.app.post(url, {'draft_id': self.public_draft._id, 'registration_choice': 'embargo'}, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'If embargo, must supply embargo end date.')

    def test_adding_embargo_prevents_project_from_being_made_public(self):
        token = token_creator(self.public_draft._id, self.user._id)
        url = '/{}draft_registrations/freeze/{}/'.format(API_BASE, token)
        res = self.app.post(url, self.embargo_payload, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['properties']['registration'], True)
        assert_equal(res.json['data']['attributes']['public'], False)


class TestDraftRegistrationUpdate(ApiTestCase):

    def setUp(self):
        super(TestDraftRegistrationUpdate, self).setUp()
        ensure_schemas()
        self.user = UserFactory.build()
        password = fake.password()
        self.password = password
        self.user.set_password(password)
        self.user.save()
        self.basic_auth = (self.user.username, password)

        self.user_two = UserFactory.build()
        self.user_two.set_password(password)
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, password)

        self.private_project = ProjectFactory(creator=self.user, is_private=True)
        self.private_draft = DraftRegistrationFactory(initiator=self.user, branched_from=self.private_project)
        self.private_url = '/{}draft_registrations/{}/'.format(API_BASE, self.private_draft._id)

        self.public_project = ProjectFactory(creator=self.user, is_public=True)
        self.public_draft = DraftRegistrationFactory(initiator=self.user, branched_from=self.public_project)
        self.public_url = '/{}draft_registrations/{}/'.format(API_BASE, self.public_draft._id)

        self.schema_name = 'OSF-Standard Pre-Data Collection Registration'
        self.registration_metadata = "{'Have you looked at the data?': 'No'}"
        self.schema_version = 1

    def test_update_node_that_is_not_registration_draft(self):
        url = '/{}draft_registrations/{}/'.format(API_BASE, self.private_project)
        res = self.app.put(url, {
            'schema_name': self.schema_name,
            'registration_metadata': self.registration_metadata,
            'schema_version': self.schema_version,
        }, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_update_node_that_does_not_exist(self):
        url = '/{}draft_registrations/{}/'.format(API_BASE, '12345')
        res = self.app.put(url, {
            'schema_name': self.schema_name,
            'registration_metadata': self.registration_metadata,
            'schema_version': self.schema_version,
        }, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_update_public_registration_draft_logged_out(self):
        res = self.app.put(self.public_url, {
            'schema_name': self.schema_name,
            'registration_metadata': self.registration_metadata,
            'schema_version': self.schema_version,
        }, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_update_public_registration_draft_logged_in(self):
        res = self.app.put(self.public_url, {
            'schema_name': self.schema_name,
            'registration_metadata': self.registration_metadata,
            'schema_version': self.schema_version,
        }, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 200)
        metadata = res.json['data']['attributes']['registration_metadata']
        registration_schema = res.json['data']['attributes']['registration_schema']
        assert_equal(metadata, self.registration_metadata)
        assert_not_equal(registration_schema, None)
        assert_equal(registration_schema, self.schema_name)

        res = self.app.put(self.public_url, {
            'schema_name': self.schema_name,
            'registration_metadata': self.registration_metadata,
            'schema_version': self.schema_version,
        }, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_update_private_registration_draft_logged_out(self):
        res = self.app.put(self.private_url, {
            'schema_name': self.schema_name,
            'registration_metadata': self.registration_metadata,
            'schema_version': self.schema_version,
        }, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_update_private_registration_draft_logged_in_contributor(self):
        res = self.app.put(self.private_url, {
            'schema_name': self.schema_name,
            'registration_metadata': self.registration_metadata,
            'schema_version': self.schema_version,
        }, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 200)
        metadata = res.json['data']['attributes']['registration_metadata']
        registration_schema = res.json['data']['attributes']['registration_schema']
        assert_equal(metadata, self.registration_metadata)
        assert_not_equal(registration_schema, None)
        assert_equal(registration_schema, self.schema_name)

    def test_update_private_registration_draft_logged_in_non_contributor(self):
        res = self.app.put(self.private_url, {
            'schema_name': self.schema_name,
            'registration_metadata': self.registration_metadata,
            'schema_version': self.schema_version,
        }, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_partial_update_private_registration_draft_logged_in_read_only_contributor(self):
        self.private_project.save()
        draft = DraftRegistrationFactory(initiator=self.user, branched_from=self.private_project)
        url = '/{}draft_registrations/{}/'.format(API_BASE, draft._id)
        res = self.app.put(url, {
            'schema_name': self.schema_name,
            'registration_metadata': self.registration_metadata,
            'schema_version': self.schema_version,
        }, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)


class TestDraftRegistrationPartialUpdate(ApiTestCase):

    def setUp(self):
        super(TestDraftRegistrationPartialUpdate, self).setUp()
        ensure_schemas()
        self.user = UserFactory.build()
        password = fake.password()
        self.password = password
        self.user.set_password(password)
        self.user.save()
        self.basic_auth = (self.user.username, password)

        self.user_two = UserFactory.build()
        self.user_two.set_password(password)
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, password)

        self.private_project = ProjectFactory(creator=self.user, is_private=True)
        self.private_draft = DraftRegistrationFactory(initiator=self.user, branched_from=self.private_project)
        self.private_url = '/{}draft_registrations/{}/'.format(API_BASE, self.private_draft._id)

        self.public_project = ProjectFactory(creator=self.user, is_public=True)
        self.public_draft = DraftRegistrationFactory(initiator=self.user, branched_from=self.public_project)
        self.public_url = '/{}draft_registrations/{}/'.format(API_BASE, self.public_draft._id)

        self.schema_name = 'OSF-Standard Pre-Data Collection Registration'
        self.registration_metadata = "{'Have you looked at the data?': 'No'}"
        self.schema_version = 1

    def test_partial_update_node_that_is_not_registration_draft(self):
        url = '/{}draft_registrations/{}/'.format(API_BASE, self.private_project)
        res = self.app.patch(url, {
            'self.schema_name': self.schema_name,
        }, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_partial_update_node_that_does_not_exist(self):
        url = '/{}draft_registrations/{}/'.format(API_BASE, '12345')
        res = self.app.patch(url, {
            'self.schema_name': self.schema_name,
        }, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    # TODO Handle schema version does not exist
    def test_partial_update_schema_version_does_not_exist(self):
        res = self.app.patch(self.public_url, {
            'schema_name': self.schema_name,
            'schema_version': 5
        }, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_partial_update_registration_schema_public_draft_registration_logged_in(self):
        res = self.app.patch(self.public_url, {
            'schema_name': self.schema_name,
        }, auth=self.basic_auth, expect_errors=True)
        registration_schema = res.json['data']['attributes']['registration_schema']
        assert_equal(registration_schema, self.schema_name)
        assert_equal(res.status_code, 200)

        res = self.app.patch(self.public_url, {
            'schema_name': self.schema_name,
            'schema_version': self.schema_version
        }, auth=self.basic_auth, expect_errors=True)
        registration_schema = res.json['data']['attributes']['registration_schema']
        assert_equal(registration_schema, self.schema_name)
        assert_equal(res.status_code, 200)

    def test_partial_update_public_draft_registration_logged_out(self):
        res = self.app.patch(self.public_url, {
            'schema_name': self.schema_name,
        }, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_partial_update_public_draft_registration_logged_in(self):
        res = self.app.patch(self.public_url, {
            'registration_metadata': self.registration_metadata,
        }, auth=self.basic_auth, expect_errors=True)
        registration_metadata = res.json['data']['attributes']['registration_metadata']
        assert_equal(registration_metadata, self.registration_metadata)
        assert_equal(res.status_code, 200)

        res = self.app.patch(self.public_url, {
             'registration_metadata': self.registration_metadata,
        }, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_partial_update_private_registration_draft_logged_out(self):
        res = self.app.patch(self.private_url, {
             'registration_metadata': self.registration_metadata,
        }, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_partial_update_private_registration_draft_logged_in_contributor(self):
        res = self.app.patch(self.private_url, {
            'registration_metadata': self.registration_metadata,
        }, auth=self.basic_auth)
        registration_metadata = res.json['data']['attributes']['registration_metadata']
        assert_equal(registration_metadata, self.registration_metadata)
        assert_equal(res.status_code, 200)

    def test_partial_update_private_registration_draft_logged_in_non_contributor(self):
        res = self.app.patch(self.private_url, {
            'registration_metadata': self.registration_metadata,
        }, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_partial_update_private_registration_draft_logged_in_read_only_contributor(self):
        self.private_project.save()
        draft = DraftRegistrationFactory(initiator=self.user, branched_from=self.private_project)
        url = '/{}draft_registrations/{}/'.format(API_BASE, draft._id)
        res = self.app.patch(url, {
            'registration_metadata': self.registration_metadata,
        }, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)


class TestDeleteDraftRegistration(ApiTestCase):

    def setUp(self):
        super(TestDeleteDraftRegistration, self).setUp()
        ensure_schemas()
        self.user = UserFactory.build()
        password = fake.password()
        self.password = password
        self.user.set_password(password)
        self.user.save()
        self.basic_auth = (self.user.username, password)

        self.user_two = UserFactory.build()
        self.user_two.set_password(password)
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, password)

        self.private_project = ProjectFactory(creator=self.user, is_private=True)
        self.private_draft = DraftRegistrationFactory(initiator=self.user, branched_from=self.private_project)
        self.private_url = '/{}draft_registrations/{}/'.format(API_BASE, self.private_draft._id)

        self.public_project = ProjectFactory(creator=self.user, is_public=True)
        self.public_draft = DraftRegistrationFactory(initiator=self.user, branched_from=self.public_project)
        self.public_url = '/{}draft_registrations/{}/'.format(API_BASE, self.public_draft._id)


    def test_delete_node_that_is_not_registration_draft(self):
        url = '/{}draft_registrations/{}/'.format(API_BASE, self.private_project)
        res = self.app.delete(url, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_delete_node_that_does_not_exist(self):
        url = '/{}draft_ registrations/{}/'.format(API_BASE, '12345')
        res = self.app.delete(url, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_delete_public_draft_registration_logged_out(self):
        res = self.app.delete(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_delete_public_draft_registration_logged_in(self):
        res = self.app.patch(self.public_url, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

        res = self.app.delete(self.public_url, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 204)
        res = self.app.get(self.public_url, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_delete_private_registration_draft_logged_out(self):
        res = self.app.delete(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_delete_private_registration_draft_logged_in_contributor(self):
        res = self.app.delete(self.private_url, auth=self.basic_auth)
        assert_equal(res.status_code, 204)
        res = self.app.get(self.private_url, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_delete_private_registration_draft_logged_in_non_contributor(self):
        res = self.app.delete(self.private_url, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_delete_private_registration_draft_logged_in_read_only_contributor(self):
        self.private_project.add_contributor(self.user_two, permissions=['read'])
        self.private_project.save()
        new_draft = DraftRegistrationFactory(initiator=self.user, branched_from=self.private_project)
        url = '/{}draft_registrations/{}/'.format(API_BASE, new_draft._id)
        res = self.app.delete(url, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)








