from girder import events, plugin
from girder.models.model_base import ValidationException
from girder.settings import SettingDefault
from girder.utility import setting_utilities
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


class GirderPlugin(plugin.GirderPlugin):
    DISPLAY_NAME = 'OpenID 1.0 Login'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        events.bind('no_password_login_attempt', 'openid', _checkOpenIdUser)
        info['apiRoot'].openid = rest.OpenId()
        SettingDefault.defaults[constants.PluginSettings.PROVIDERS] = []
