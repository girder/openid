import os

from girder import events, logger, plugin
from girder.models.model_base import ValidationException
from girder.settings import SettingDefault
from girder.utility import setting_utilities
from openid.fetchers import HTTPFetcher, HTTPResponse, setDefaultFetcher
import requests

from . import rest, constants


@setting_utilities.validator(constants.PluginSettings.PROVIDERS)
def validateProvidersEnabled(doc):
    if not isinstance(doc['value'], (list, tuple)):
        raise ValidationException('The enabled providers must be a list.', 'value')

    for provider in doc['value']:
        if not isinstance(provider, dict):
            raise ValidationException('Providers should be JSON objects.')
        if 'url' not in provider or 'name' not in provider:
            raise ValidationException('Providers must have a "name" and "url" field.')


@setting_utilities.validator(constants.PluginSettings.IGNORE_REGISTRATION_POLICY)
def validateIgnoreRegistrationPolicy(doc):
    if not isinstance(doc['value'], bool):
        raise ValidationException('Ignore registration policy setting must be boolean.', 'value')


def _checkOpenIdUser(event):
    """
    If an OpenID user without a password tries to log in with a password, we
    want to give them a useful error message.
    """
    if event.info['user'].get('openid'):
        raise ValidationException(
            'You don\'t have a password. Please log in with OpenID, or use the '
            'password reset link.')


class _CustomCAFetcher(HTTPFetcher):
    def __init__(self, verify, *args, **kwargs):
        super(_CustomCAFetcher, self).__init__(*args, **kwargs)
        self._verify = verify

    def fetch(self, url, body=None, headers=None):
        headers = headers or {}
        if body:
            method = 'POST'
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        else:
            method = 'GET'

        with requests.session() as s:
            response = s.request(method, url, data=body, headers=headers, verify=self._verify)

        return HTTPResponse(response.url, response.status_code, response.headers, response.content)


class GirderPlugin(plugin.GirderPlugin):
    DISPLAY_NAME = 'OpenID 1.0 Login'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        events.bind('no_password_login_attempt', 'openid', _checkOpenIdUser)
        info['apiRoot'].openid = rest.OpenId()
        SettingDefault.defaults[constants.PluginSettings.PROVIDERS] = []

        if 'GIRDER_REQUESTS_VERIFY' in os.environ:
            path = os.environ['GIRDER_REQUESTS_VERIFY']
            if not os.path.isfile(path):
                raise Exception('Requests cert not found: %s' % path)
            # We use a custom fetcher class and set it as the default to support customization
            # of the "verify" parameter of the requests session
            logger.info('OpenID: using verify value=%s' % path)
            setDefaultFetcher(_CustomCAFetcher(path), wrap_exceptions=False)
