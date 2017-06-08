#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

from girder import events
from girder.constants import SettingDefault
from girder.models.model_base import ValidationException
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


def checkOpenIdUser(event):
    """
    If an OpenID user without a password tries to log in with a password, we
    want to give them a useful error message.
    """
    user = event.info['user']
    if user.get('openid'):
        raise ValidationException(
            'You don\'t have a password. Please log in with OpenID, or use the '
            'password reset link.')


def load(info):
    events.bind('no_password_login_attempt', 'openid', checkOpenIdUser)

    info['apiRoot'].openid = rest.OpenId()

    SettingDefault.defaults[constants.PluginSettings.PROVIDERS] = []
