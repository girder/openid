import cherrypy
import re
import ssl
from openid.consumer import consumer
from openid.extensions import ax

from girder import config
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import getApiUrl, setResponseHeader, rawResponse, Resource, RestException
from girder.api import access
from girder.settings import SettingKey
from girder.models.setting import Setting
from girder.models.user import User
from . import constants, store

_REQUIRED_AX_ATTRS = {
    'EMAIL': 'http://axschema.org/contact/email',
    'FIRST': 'http://axschema.org/namePerson/first',
    'LAST': 'http://axschema.org/namePerson/last'
}

_xrdsDoc = """
<xrds:XRDS
    xmlns:xrds="xri://$xrds"
    xmlns:openid="http://openid.net/xmlns/1.0"
    xmlns="xri://$xrd*($v*2.0)">
  <XRD>
    <Service priority="1">
      <Type>http://specs.openid.net/auth/2.0/return_to</Type>
      <URI>{returnTo}</URI>
    </Service>
  </XRD>
</xrds:XRDS>
"""


class OpenId(Resource):
    def __init__(self):
        super(OpenId, self).__init__()
        self.resourceName = 'openid'

        self.route('GET', (), self.xrds)
        self.route('GET', ('provider',), self.listProviders)
        self.route('GET', ('login',), self.login)
        self.route('GET', ('callback',), self.callback)

        self._store = store.GirderStore()
        # TODO remove awful monkey patch that circumvents SSL cert verification
        ssl._create_default_https_context = ssl._create_unverified_context

    @access.unauthenticated
    @rawResponse
    @autoDescribeRoute(
        Description('Get the XRDS document for this OpenID RP.')
    )
    def xrds(self):
        apiUrl = getApiUrl()
        setResponseHeader('X-XRDS-Location', apiUrl + '/openid')
        return _xrdsDoc.format(returnTo=apiUrl + '/openid/callback')

    @access.unauthenticated
    @autoDescribeRoute(
        Description('Get the list of enabled OpenId providers and their URLs.')
    )
    def listProviders(self):
       return Setting().get(constants.PluginSettings.PROVIDERS)

    @access.unauthenticated
    @autoDescribeRoute(
        Description('Login using a specific OpenID provider URL.')
        .param('url', 'The OpenID provider URL to use for authentication.')
    )
    def login(self, url):
        if url not in set(p['url'] for p in Setting().get(constants.PluginSettings.PROVIDERS)):
            raise RestException('Invalid OpenID provider URL.')

        request = consumer.Consumer(session={}, store=self._store).begin(url)
        request.addExtension(self._getAxFetchRequest())
        apiUrl = getApiUrl()
        raise cherrypy.HTTPRedirect(
            request.redirectURL(apiUrl + '/openid', apiUrl + '/openid/callback'))

    @access.unauthenticated
    @autoDescribeRoute(
        Description('Callback called by OpenID providers.'),
        hide=True
    )
    def callback(self, params):
        apiUrl = getApiUrl()
        currUrl = apiUrl + '/openid/callback'
        csmr = consumer.Consumer(session={}, store=self._store)
        resp = csmr.complete(params, currUrl)

        # TODO redirect handling
        redirect = apiUrl[:apiUrl.find('/api/v1')]

        if resp.status == consumer.SUCCESS:
            axInfo = ax.FetchResponse.fromSuccessResponse(resp)

            if axInfo is None:
                raise RestException('Did not receive user info from OpenId Provider.')

            first = axInfo.getSingle(_REQUIRED_AX_ATTRS['FIRST'])
            last = axInfo.getSingle(_REQUIRED_AX_ATTRS['LAST'])
            email = axInfo.getSingle(_REQUIRED_AX_ATTRS['EMAIL'])
            openId = resp.getDisplayIdentifier()

            user = self._createOrReuseUser(first, last, email, openId)
            self.sendAuthTokenCookie(user)

            raise cherrypy.HTTPRedirect(redirect)
        elif resp.status == consumer.CANCEL:
            raise cherrypy.HTTPRedirect(redirect + '#openid/canceled')
        else:
            # TODO log details?
            raise RestException('OpenId Authentication failed (%s).' % resp.status)

    def _getAxFetchRequest(self):
        req = ax.FetchRequest()
        for attr in _REQUIRED_AX_ATTRS.values():
            req.add(ax.AttrInfo(attr))
        return req

    def _createOrReuseUser(self, firstName, lastName, email, openId):
        # Try finding by ID first, since a user can change their email address
        query = {
            'openid.identifier': openId
        }

        user = User().findOne(query)
        setId = not user
        dirty = False

        # Create the user if it's still not found
        if not user:
            ignore = constants.PluginSettings.IGNORE_REGISTRATION_POLICY
            policy = SettingKey.REGISTRATION_POLICY

            if not Setting().get(ignore) and Setting().get(policy) == 'closed':
                raise RestException(
                    'Registration on this instance is closed. Contact an '
                    'administrator to create an account for you.')
            login = self._deriveLogin(email, firstName, lastName)

            user = User().createUser(
                login=login, password=None, firstName=firstName,
                lastName=lastName, email=email)
        else:
            # Migrate from a legacy format where only 1 provider was stored
            # Update user data from provider
            if email != user['email']:
                user['email'] = email
                dirty = True
            # Don't set names to empty string
            if firstName != user['firstName'] and firstName:
                user['firstName'] = firstName
                dirty = True
            if lastName != user['lastName'] and lastName:
                user['lastName'] = lastName
                dirty = True
        if setId:
            user['openid'] = {
                'identifier': openId
            }
            dirty = True
        if dirty:
            user = User().save(user)

        return user

    def _generateLogins(self, email, firstName, lastName):
        """
        Generate a series of reasonable login names for a new user based on
        their basic information sent to us by the provider.
        """
        # Next try to use the prefix from their email address
        prefix = email.split('@')[0]
        yield prefix
        yield re.sub('[\W_]+', '', prefix)

        # Finally try to use their first and last name
        yield '%s%s' % (firstName, lastName)

        for i in range(1, 6):
            yield '%s%s%d' % (firstName, lastName, i)

    def _deriveLogin(self, email, firstName, lastName):
        """
        Attempt to automatically create a login name from existing user
        information from OAuth2 providers. Attempts to generate it from the
        username on the provider, the email address, or first and last name. If
        not possible, returns None and it is left to the caller to generate
        their own login for the user or choose to fail.

        :param email: The email address.
        :type email: str
        """
        # Note, the user's OAuth2 ID should never be used to form a login name,
        # as many OAuth2 services consider that to be private data
        for login in self._generateLogins(email, firstName, lastName):
            login = login.lower()
            if self._testLogin(login):
                return login

        raise Exception('Could not generate a unique login name for %s (%s %s)'
                        % (email, firstName, lastName))

    def _testLogin(self, login):
        """
        When attempting to generate a username, use this to test if the given
        name is valid.
        """
        # TODO this will fail if login regex is removed
        regex = config.getConfig()['users']['login_regex']

        # Still doesn't match regex, we're hosed
        if not re.match(regex, login):
            return False

        # See if this is already taken.
        return User().findOne({'login': login}) is None
