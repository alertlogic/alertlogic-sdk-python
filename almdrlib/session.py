# -*- coding: utf-8 -*-

"""
    almdrlib.session
    ~~~~~~~~~~~~~~~~
    almdrlib authentication/authorization
"""
import logging

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import re

from almdrlib.config import Config
from almdrlib.region import Region
from almdrlib.client import Client
import alsdkdefs

logger = logging.getLogger(__name__)


class AuthenticationException(Exception):
    def __init__(self, message):
        super(AuthenticationException, self).__init__(
                f"authentication error: {message}")


class Session():
    """
    Authenticates against Alert Logic AIMS service and
    stores session information (token and account id).
    Additionally objects of this class can be used as auth modules
    for the requests lib, more info:
    http://docs.python-requests.org/en/master/user/authentication/#new-forms-of-authentication
    """

    _access_key_id = None
    _secret_key = None

    def __init__(
            self, access_key_id=None, secret_key=None, aims_token=None,
            account_id=None, profile=None, global_endpoint=None,
            residency="default", raise_for_status=True):
        """
        :param region: a Region object
        :param access_key_id: your Alert Logic ActiveWatchaccess_key_id
                              or username
        :param secret_key: your Alert Logic ActiveWatchsecret_key or password
        :param aims_token: aims_token to be used for authentication.
                           If aims_token is specified,
                           access_key_id and secret_key paramters are ignored
        :param account_id: Alert Logic Account ID to initialize a session for.
                            Unless account_id is provided explicitly
                            during service connection initialization,
                            this account id is used.
                            If this parameter isn't specified,
                            the account id of the access_key_id is used.
        :param: profile: name of the profile section of the configuration file
        :param: global_endpoint: Name of the global endpoint.
                                 'production', 'integration', or 'map' are
                                 the only valid values
        :param residency: Data residency name to perform
                          data residency dependend actions.
                          Currently, 'default', 'us' and 'emea'
                          are the only valid entries
        :param raise_for_status: Raise an exception for failed http requests
                                 instead of returning response object
        """

        # Setup session object
        self._session = requests.Session()
        retries = Retry(
                total=5,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
                method_whitelist=[
                    "HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
                )
        self._session.mount('https://', HTTPAdapter(max_retries=retries))

        # Initialize session's state
        self._token = None
        self._defaults = None
        self._init_session(
                access_key_id=access_key_id,
                secret_key=secret_key,
                aims_token=aims_token,
                account_id=account_id,
                profile=profile,
                global_endpoint=global_endpoint,
                residency=residency,
                raise_for_status=raise_for_status)

    def _init_session(self, *args, **kwargs):
        """ Initialize session object based on the kwargs provided """

        if not len(kwargs):
            return

        access_key_id = kwargs.get('access_key_id')
        secret_key = kwargs.get('secret_key')
        account_id = kwargs.get('account_id')
        profile = kwargs.get('profile')
        global_endpoint = kwargs.get('global_endpoint')
        residency = kwargs.get('residency', 'default')
        aims_token = kwargs.get('aims_token')

        self._config = Config(
                access_key_id=access_key_id,
                secret_key=secret_key,
                account_id=account_id,
                profile=profile,
                global_endpoint=global_endpoint,
                residency=residency
            )

        self._account_id = self._config.account_id
        self._residency = self._config.residency
        self._global_endpoint = self._config.global_endpoint
        self._endpoint_map = self._config.endpoint_map
        self._global_endpoint_url = Region.get_global_endpoint(self._global_endpoint)
        self._raise_for_status = kwargs.get('raise_for_status')

        if aims_token:
            self._token = aims_token
        else:
            self._access_key_id, self._secret_key = self._config.get_auth()

        logger.debug(
                "Initialized session. "
                f"access_key_id={self._access_key_id}, "
                f"account_id={self._account_id}, "
                f"profile={profile}, "
                f"global_endpoint={self._global_endpoint}, "
                f"residency={self._residency}"
            )

    def _authenticate(self):
        """
        Authenticates against Access and Identity Management Service (AIMS)
        more info:
        https://console.cloudinsight.alertlogic.com/api/aims/#api-AIMS_Authentication_and_Authorization_Resources-Authenticate
        """

        if not self._token:
            if self._access_key_id == "skip" and self._secret_key == "skip":
                logger.info(
                        f"Skipping authentication."
                    )
                self._token = ""
                self._account_id = ""
                self._account_name = ""
                self._user_id = ""
                return
            logger.info(
                    f"Authenticating '{self._access_key_id}' " +
                    f"user against '{self._global_endpoint_url}' endpoint."
                )
            try:
                self._session.auth = (self._access_key_id, self._secret_key)
                response = self._session.post(
                        f"{self._global_endpoint_url}/aims/v1/authenticate")
                response.raise_for_status()

                auth_info = response.json()
                account_info = auth_info["authentication"]["account"]
                self._token = auth_info["authentication"]["token"]
                self._user_id = auth_info["authentication"]["user"]["id"]
                logger.info(f'Authenticated user {auth_info["authentication"]["user"]["id"]}')

            except requests.exceptions.HTTPError as e:
                raise AuthenticationException(f"invalid http response {e}")
            except (KeyError, TypeError, ValueError):
                raise AuthenticationException("token not found in response")
        else:
            logger.info("Authenticating using aims token " +
                        f"against '{self._global_endpoint_url}' endpoint.")
            try:
                response = self._session.get(
                        f"{self._global_endpoint_url}/aims/v1/token_info",
                        headers={'x-aims-auth-token': self._token})
                response.raise_for_status()
                account_info = response.json()["account"]

            except requests.exceptions.HTTPError:
                self._token = None
                return self._authenticate()
            except (KeyError, TypeError, ValueError):
                raise AuthenticationException(
                        "account information not found in response")

        if self._account_id is None:
            try:
                self._account_id = account_info["id"]
                self._account_name = account_info["name"]
            except (KeyError, TypeError, ValueError):
                raise AuthenticationException(
                        "account information not found in response")

    def __call__(self, r):
        """
        requests lib auth module callback
        """
        if self._token is None:
            self._authenticate()
        r.headers["x-aims-auth-token"] = self._token
        return r

    def client(self, service_name, version=None, *args, **kwargs):
        """
        Create Service's client class
        """

        self._init_session(**kwargs)

        # Create Service's module
        module_name = service_name.capitalize()
        class_name = "Client"

        #
        # Init function for the dynamically created class,
        # which is derived from almdrlib.client.Client
        #
        def __init__(self,
                     name,
                     session=self,
                     version=None,
                     *args,
                     **kwargs):
            super(self.__class__, self).__init__(name=name,
                                                 session=session,
                                                 version=version)

        ServiceClient = type(class_name,
                             (Client,),
                             {
                                 '__init__': __init__,
                                 '__module__': module_name
                             })

        _client = ServiceClient(service_name, session=self, version=version)
        logger.debug(
            "Created " +
            f"{_client.__class__.__module__}.{_client.__class__.__name__}" +
            " class instance")
        return _client

    def get_url(self, service_name, account_id=None):
        if self._global_endpoint == "map":
            return self.get_mapped_url(service_name, account_id)
        elif re.match(r'^(http|https)://.*$', self._global_endpoint):
            return self._global_endpoint
        try:
            response = self.request(
                'get',
                Region.get_endpoint_url(self._global_endpoint_url,
                                        service_name,
                                        account_id or self.account_id,
                                        self.residency),
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise AuthenticationException(
                    f"invalid http response from endpoints service {e}"
                )
        return "https://{}".format(response.json()[service_name])

    def get_mapped_url(self, service_name, account_id):
        map = self._endpoint_map
        return map[service_name]

    def request(
            self,
            method,
            url,
            params={},
            headers={},
            cookies={},
            **kwargs):

        # Make sure we've authenticated
        if self._token is None:
            self._authenticate()

        # it's too easy to include the AIMS token when pasting debug logs, so redact it in
        # the logging statement.
        headers.update({'x-aims-auth-token': "REDACTED"})

        logger.debug(f"Calling '{method}' method. " +
                     f"URL: '{url}'. " +
                     f"Params: '{params}' " +
                     f"Headers: '{headers}' " +
                     f"Cookies: '{cookies}' " +
                     f"Args: '{kwargs}'")

        headers.update({'x-aims-auth-token': self._token})

        response = self._session.request(
                method, url,
                params=params,
                headers=headers,
                cookies=cookies,
                **kwargs)
        if self._raise_for_status:
            response.raise_for_status()
        logger.debug(f"'{method}' method for URL: '{url}' returned "
                     f"'{response.status_code}' status code "
                     f"in '{response.elapsed.total_seconds()}' seconds")
        return response

    def get_default(self, name):
        if name == 'account_id':
            return self.account_id

        return None

    def validate_server(self, spec):
        if 'x-alertlogic-global-endpoint' not in spec:
            return True

        return self._global_endpoint == spec['x-alertlogic-global-endpoint']

    @staticmethod
    def list_services():
        return alsdkdefs.list_services()

    @staticmethod
    def get_service_api(service_name, version=None):
        client = Client(service_name, version=version)
        model = {'info': client.info}
        operations = {}
        for op_name, operation in client.operations.items():
            operations[op_name] = operation.get_schema()
        model.update({'operations': dict(sorted(operations.items()))})
        return model

    @property
    def account_id(self):
        if self._account_id is None:
            self._authenticate()
        return self._account_id

    @property
    def residency(self):
        return self._residency

    @property
    def account_name(self):
        return self._account_name

    @property
    def global_endpoint(self):
        return self._global_endpoint

    @property
    def global_endpoint_url(self):
        return self._global_endpoint_url

    @property
    def token(self):
        return self._token

    @property
    def user_id(self):
        return self._user_id
