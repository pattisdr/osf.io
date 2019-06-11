import pytest
import httplib as http

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
    DismissedAlertFactory,
)

@pytest.mark.django_db
class TestDismissedAlertDetail:

    def test_dismissed_alerts_detail(self, app):

        user = AuthUserFactory()
        alert_id = 'adblock'
        alert_location = 'jc3vf/settings/'
        url_alerts_detail = '/{}alerts/{}/'.format(API_BASE, alert_id)

        DismissedAlertFactory(
            user=user,
            location=alert_location,
            _id=alert_id)

        # test_alerts_get_success
        res = app.get(url_alerts_detail, auth=user.auth)
        assert res.status_code == http.OK
        assert res.json['data']['id'] == alert_id
        assert res.json['data']['attributes']['location'] == alert_location
        assert alert_id in res.json['data']['links']['self']
