import mock
import pytest

from addons.wiki.tests.factories import WikiFactory, WikiVersionFactory
from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    RegistrationFactory,
)
from rest_framework import exceptions


@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.mark.django_db
class TestNodeWikiList:

    @pytest.fixture()
    def add_project_wiki_page(self):
        def add_page(node, user):
            with mock.patch('osf.models.AbstractNode.update_search'):
                wiki_page = WikiFactory(node=node, user=user)
                return WikiVersionFactory(wiki_page=wiki_page)
        return add_page

    @pytest.fixture()
    def non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def public_project(self, user):
        return ProjectFactory(is_public=True, creator=user)

    @pytest.fixture()
    def public_wiki(self, add_project_wiki_page, user, public_project):
        return add_project_wiki_page(public_project, user)

    @pytest.fixture()
    def public_url(self, public_project, public_wiki):
        return '/{}nodes/{}/wikis/'.format(API_BASE, public_project._id)

    @pytest.fixture()
    def private_project(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def private_wiki(self, add_project_wiki_page, user, private_project):
        return add_project_wiki_page(private_project, user)

    @pytest.fixture()
    def private_url(self, private_project, private_wiki):
        return '/{}nodes/{}/wikis/'.format(API_BASE, private_project._id)

    @pytest.fixture()
    def public_registration(self, user, public_project, public_wiki):
        public_registration = RegistrationFactory(project=public_project, user=user, is_public=True)
        return public_registration

    @pytest.fixture()
    def public_registration_url(self, public_registration):
        return '/{}registrations/{}/wikis/'.format(API_BASE, public_registration._id)

    @pytest.fixture()
    def private_registration(self, user, private_project, private_wiki):
        private_registration = RegistrationFactory(project=private_project, user=user)
        return private_registration

    @pytest.fixture()
    def private_registration_url(self, private_registration):
        return '/{}registrations/{}/wikis/'.format(API_BASE, private_registration._id)

    def test_return_wikis(self, app, user, non_contrib, private_registration, public_wiki, private_wiki, public_url, private_url, private_registration_url):

    #   test_return_public_node_wikis_logged_out_user
        res = app.get(public_url)
        assert res.status_code == 200
        wiki_ids = [wiki['id'] for wiki in res.json['data']]
        assert public_wiki._id in wiki_ids

    #   test_return_public_node_wikis_logged_in_non_contributor
        res = app.get(public_url, auth=non_contrib.auth)
        assert res.status_code == 200
        wiki_ids = [wiki['id'] for wiki in res.json['data']]
        assert public_wiki._id in wiki_ids

    #   test_return_public_node_wikis_logged_in_contributor
        res = app.get(public_url, auth=user.auth)
        assert res.status_code == 200
        wiki_ids = [wiki['id'] for wiki in res.json['data']]
        assert public_wiki._id in wiki_ids

    #   test_return_private_node_wikis_logged_out_user
        res = app.get(private_url, expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    #   test_return_private_node_wikis_logged_in_non_contributor
        res = app.get(private_url, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    #   test_return_private_node_wikis_logged_in_contributor
        res = app.get(private_url, auth=user.auth)
        assert res.status_code == 200
        wiki_ids = [wiki['id'] for wiki in res.json['data']]
        assert private_wiki._id in wiki_ids

    #   test_return_registration_wikis_logged_out_user
        res = app.get(private_registration_url, expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    #   test_return_registration_wikis_logged_in_non_contributor
        res = app.get(private_registration_url, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    #   test_return_registration_wikis_logged_in_contributor
        res = app.get(private_registration_url, auth=user.auth)
        assert res.status_code == 200
        wiki_ids = [wiki['id'] for wiki in res.json['data']]
        assert private_registration.get_wiki_version('home')._id in wiki_ids

    def test_wikis_not_returned_for_withdrawn_registration(self, app, user, private_registration, private_registration_url):
        private_registration.is_public = True
        withdrawal = private_registration.retract_registration(user=user, save=True)
        token = withdrawal.approval_state.values()[0]['approval_token']
        # TODO: Remove mocking when StoredFileNode is implemented
        with mock.patch('osf.models.AbstractNode.update_search'):
            withdrawal.approve_retraction(user, token)
            withdrawal.save()
        res = app.get(private_registration_url, auth=user.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    def test_relationship_links(self, app, user, public_project, private_project, public_registration, private_registration, public_url, private_url, public_registration_url, private_registration_url):

    #   test_public_node_wikis_relationship_links
        res = app.get(public_url)
        expected_nodes_relationship_url = '{}nodes/{}/'.format(API_BASE, public_project._id)
        expected_comments_relationship_url = '{}nodes/{}/comments/'.format(API_BASE, public_project._id)
        assert expected_nodes_relationship_url in res.json['data'][0]['relationships']['node']['links']['related']['href']
        assert expected_comments_relationship_url in res.json['data'][0]['relationships']['comments']['links']['related']['href']

    #   test_private_node_wikis_relationship_links
        res = app.get(private_url, auth=user.auth)
        expected_nodes_relationship_url = '{}nodes/{}/'.format(API_BASE, private_project._id)
        expected_comments_relationship_url = '{}nodes/{}/comments/'.format(API_BASE, private_project._id)
        assert expected_nodes_relationship_url in res.json['data'][0]['relationships']['node']['links']['related']['href']
        assert expected_comments_relationship_url in res.json['data'][0]['relationships']['comments']['links']['related']['href']

    #   test_public_registration_wikis_relationship_links
        res = app.get(public_registration_url)
        expected_nodes_relationship_url = '{}registrations/{}/'.format(API_BASE, public_registration._id)
        expected_comments_relationship_url = '{}registrations/{}/comments/'.format(API_BASE, public_registration._id)
        assert expected_nodes_relationship_url in res.json['data'][0]['relationships']['node']['links']['related']['href']
        assert expected_comments_relationship_url in res.json['data'][0]['relationships']['comments']['links']['related']['href']

    #   test_private_registration_wikis_relationship_links
        res = app.get(private_registration_url, auth=user.auth)
        expected_nodes_relationship_url = '{}registrations/{}/'.format(API_BASE, private_registration._id)
        expected_comments_relationship_url = '{}registrations/{}/comments/'.format(API_BASE, private_registration._id)
        assert expected_nodes_relationship_url in res.json['data'][0]['relationships']['node']['links']['related']['href']
        assert expected_comments_relationship_url in res.json['data'][0]['relationships']['comments']['links']['related']['href']

    def test_not_returned(self, app, public_project, public_registration, public_url, public_registration_url):

    #   test_registration_wikis_not_returned_from_nodes_endpoint
        res = app.get(public_url)
        node_relationships = [
            node_wiki['relationships']['node']['links']['related']['href']
            for node_wiki in res.json['data']
        ]
        assert res.status_code == 200
        assert len(node_relationships) == 1
        assert public_project._id in node_relationships[0]

    #   test_node_wikis_not_returned_from_registrations_endpoint
        res = app.get(public_registration_url)
        node_relationships = [
            node_wiki['relationships']['node']['links']['related']['href']
            for node_wiki in res.json['data']
            ]
        assert res.status_code == 200
        assert len(node_relationships) == 1
        assert public_registration._id in node_relationships[0]


@pytest.mark.django_db
class TestFilterNodeWikiList:

    @pytest.fixture()
    def private_project(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def base_url(self, private_project):
        return '/{}nodes/{}/wikis/'.format(API_BASE, private_project._id)

    @pytest.fixture()
    def wiki(self, user, private_project):
        with mock.patch('osf.models.AbstractNode.update_search'):
            wiki_page = WikiFactory(node=private_project, user=user)
            return WikiVersionFactory(wiki_page=wiki_page)

    @pytest.fixture()
    def date(self, wiki):
        return wiki.date.strftime('%Y-%m-%dT%H:%M:%S.%f')

    def test_filter_node_wiki_list(self, app, user, wiki, date, base_url):

    #   test_node_wikis_with_no_filter_returns_all
        res = app.get(base_url, auth=user.auth)
        wiki_ids = [item['id'] for item in res.json['data']]

        assert wiki._id in wiki_ids

    #   test_filter_wikis_by_page_name
        url = base_url + '?filter[name]=home'
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['attributes']['name'] == 'home'

    #   test_filter_wikis_modified_on_date
        url = base_url + '?filter[date_modified][eq]={}'.format(date)
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 1

    #   test_filter_wikis_modified_before_date
        url = base_url + '?filter[date_modified][lt]={}'.format(date)
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 0

    #   test_filter_wikis_modified_after_date
        url = base_url + '?filter[date_modified][gt]={}'.format(date)
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 0
