import httplib as http

import furl
from werkzeug.datastructures import ImmutableDict
from framework.exceptions import HTTPError

from website import mails
from website.settings import DOMAIN

CAMPAIGNS = ImmutableDict({
    'prereg': {
        'system_tag': 'prereg_challenge_campaign',
        'redirect_url': lambda: furl.furl(DOMAIN).add(path='prereg/').url,
        'confirmation_email_template': mails.CONFIRM_EMAIL_PREREG,
    },
    'institution': {
        'system_tag': 'institution_campaign',
        'redirect_url': lambda: ''
    },
    'erpc': {
        'system_tag': 'erp_challenge_campaign',
        'redirect_url': lambda: furl.furl(DOMAIN).add(path='erpc/').url,
        'confirmation_email_template': mails.CONFIRM_EMAIL_ERPC,
    },
    # Various preprint services
    # Each preprint service will offer their own campaign with appropriate distinct branding
    'osf-preprints': {
        'system_tag': 'osf_preprints',
        'redirect_url': lambda: furl.furl(DOMAIN).add(path='preprints/').url,
        'confirmation_email_template': mails.CONFIRM_EMAIL_PREPRINTS_OSF,
        'proxy_login': True,
    }
})


def system_tag_for_campaign(campaign):
    if campaign in CAMPAIGNS:
        return CAMPAIGNS[campaign]['system_tag']
    return None


def email_template_for_campaign(campaign):
    if campaign in CAMPAIGNS:
        return CAMPAIGNS[campaign]['confirmation_email_template']


def campaign_for_user(user):
    for campaign, config in CAMPAIGNS.items():
        # TODO: This is a bit of a one-off to support the Prereg Challenge.
        # We should think more about the campaigns architecture and in
        # particular define the behavior if the user has more than one
        # campagin tag in their system_tags.
        if config['system_tag'] in user.system_tags:
            return campaign


def is_proxy_login(campaign):
    if campaign not in CAMPAIGNS:
        raise HTTPError(http.BAD_REQUEST)
    else:
        return CAMPAIGNS[campaign].get('proxy_login')


def campaign_url_for(campaign):
    if campaign not in CAMPAIGNS:
        raise HTTPError(http.BAD_REQUEST)
    else:
        return CAMPAIGNS[campaign]['redirect_url']()
