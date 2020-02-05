# -*- coding: utf-8 -*-

"""
    almdrlib.session
    ~~~~~~~~~~~~~~
    almdrlib authentication/authorization
"""
import os
import requests
import almdrlib
import logging
from almdrlib.config import Config
from almdrlib.region import Region
from almdrlib.client import Client

logger = logging.getLogger(__name__)

class AuthenticationException(Exception):
    def __init__(self, message):
        super(AuthenticationException, self).__init__("authentication error: {}".format(message))


class Session():
    """
    Authenticates against Alert Logic ActiveWatchaims service and stores session information (token and account id),
    additionally objects of this class can be used as auth modules for the requests lib, more info:
    http://docs.python-requests.org/en/master/user/authentication/#new-forms-of-authentication
    """

    def __init__(self, access_key_id=None, secret_key=None, aims_token=None,
            account_id=None, profile=None, global_endpoint = None, residency="us",
            raise_for_status=True):
        """
        :param region: a Region object
        :param access_key_id: your Alert Logic ActiveWatchaccess_key_id or username
        :param secret_key: your Alert Logic ActiveWatchsecret_key or password
        :param aims_token: aims_token to be used for authentication. If aims_token is specified, access_key_id and secret_key paramters are ignored
        : param account_id: Alert Logic Account ID to initialize a session for. Unless account_id is provided explicitly during service connection initialization, this account id is used. If this parameter isn't specified, the account id of the access_key_id is used.
        :param: profile: name of the profile section of the configuration file
        :param: global_endpoint: Name of the global endpoint. 'production' or 'integration' are the only valid values
        :param residency: Data residency name to perform data residency dependend actions. Currently, 'default', 'us' and 'emea' are the only valid entries
        :param raise_for_status: Raise an exception for faild http requests instead of returning response object
        """
        
        self._config = Config(access_key_id=access_key_id, secret_key=secret_key, account_id=account_id,
                                profile=profile, global_endpoint=global_endpoint, residency=residency)

        self._token = None
        self._defaults = None
        self._account_id = self._config.account_id
        self._residency = self._config.residency
        self._global_endpoint = self._config.global_endpoint
        self._global_endpoint_url = Region.get_global_endpoint(self._global_endpoint)
        self._raise_for_status = raise_for_status

        if aims_token:
            self._token = aims_token
        else:
            self._access_key_id, self._secret_key = self._config.get_auth()

    def _set_credentials(self, access_key_id, secret_key, aims_token):
        self._access_key_id = access_key_id
        self._secret_key = secret_key
        self._token = aims_token

    def _authenticate(self):
        """
        Authenticates against alertlogic ActiveWatch Access and Identity Management Service (AIMS)
        more info:
        https://console.cloudinsight.alertlogic.com/api/aims/#api-AIMS_Authentication_and_Authorization_Resources-Authenticate
        """
        logger.info(f"Authenticating '{self._access_key_id}' user against '{self._global_endpoint_url}' endpoint.")
        try:
            auth = requests.auth.HTTPBasicAuth(self._access_key_id, self._secret_key)
            response = requests.post(self._global_endpoint_url + "/aims/v1/authenticate", auth=auth)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise AuthenticationException("invalid http response {}".format(e))

        try:
            self._token = response.json()["authentication"]["token"]
        except (KeyError, TypeError, ValueError):
            raise AuthenticationException("token not found in response")

        if self._account_id is None:
            try:
                self._account_id = response.json()["authentication"]["account"]["id"]
            except (KeyError, TypeError, ValueError):
                raise AuthenticationException("account id not found in response")

        try:
            self._account_name = response.json()["authentication"]["account"]["name"]
        except (KeyError, TypeError, ValueError):
            raise AuthenticationException("account name not found in response")
        
    def __call__(self, r):
        """
        requests lib auth module callback
        """
        if self._token is None:
            self._authenticate()
        r.headers["x-aims-auth-token"] = self._token
        return r

    def client(self, service_name, version=None, *args, **kwargs):
        self.__init__(*args, **kwargs)
        return Client(service_name, session=self, version=version)

    def get_url(self, service_name, account_id = None):
        try:
            response = requests.get(
                Region.get_endpoint_url(self._global_endpoint_url,
                                        service_name,
                                        account_id or self.account_id,
                                        self.residency)
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise AuthenticationException("invalid http response from endpoints service {}".format(e))
        return "https://{}".format(response.json()[service_name])

    def request(self, method, url, params={}, headers={}, cookies={}, **kwargs):
        headers.update({'x-aims-auth-token': self._token})
        logger.debug(f"Calling '{method}' method. URL: '{url}'. Params: '{params}' Headers: '{headers}' Cookies: '{cookies}' Args: '{kwargs}'")
        response = requests.request(method, url, params=params, headers=headers, cookies=cookies, **kwargs)
        if self._raise_for_status:
            response.raise_for_status()
        logger.debug(f"'{method}' method for URL: '{url}' returned '{response.status_code}' status code")
        return response

    def get_default(self, name):
        if name == 'account_id':
            return self.account_id

        return None

    @staticmethod
    def list_services():
        service_api_dir = f"{os.path.dirname(__file__)}/apis"
        return next(os.walk(service_api_dir))[1]

    def get_service_api(self, service_name, version=None):
        client = self.client(service_name, version)
        model = {'info': client.info}
        operations = {}
        for op_name, operation in client.operations.items():
            operations[op_name] = operation.get_schema()
        model.update({'operations': operations})
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
