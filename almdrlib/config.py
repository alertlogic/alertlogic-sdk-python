# -*- coding: utf-8 -*-

import os.path
import configparser
import logging
import almdrlib.constants

logger = logging.getLogger(__name__)


class ConfigException(Exception):
    def __init__(self, message):
        super(ConfigException, self).__init__("config error: {message}")


class Config():
    """
    Reads configuraiton parameters from either environment variables
        or from configuration file

    Environment Variables:
    ALERTLOGIC_CONFIG - Location of the configuration file. If not specified,
    ~/.almdrlib/credentials is used
    ALERTLOGIC_PROFILE - Profile to be used.
    If not specified [default] section is used
    ALERTLOGIC_ACCESS_KEY_ID - Acceess Key Id
    ALERTLOGIC_SECRET_KEY - Secret Key
    ALERTLOGIC_ENDPOINT - production or integration are supported values
    ALERTLOGIC_ACCOUNT_ID - Account Id to perform operatins against.
    ALERTLOGIC_RESIDENCY - Data Residency when creating new deployments
    ALERTLOGIC_API  - Directory where OpenAPI yaml files reside

    Config File section values
    access_key_id - User's AIMS Access Key ID
    secret_key - Secret Key associated with 'access_key_id'
    global_endpoint - if not specified, 'production' endpoint is used
    account_id - if not specified, the account id of the access_key_id is used
    residency - if not specified, 'us' residency is used

    NOTE: Environment variables take precedence over values
          specified in configuration file
    """
    def __init__(self,
                 access_key_id=None,
                 secret_key=None,
                 account_id=None,
                 profile=None,
                 global_endpoint=None,
                 residency=None):
        self._config_file = os.environ.get('ALERTLOGIC_CONFIG')
        if self._config_file is None:
            self._config_file = almdrlib.constants.DEFAULT_CONFIG_FILE

        logger.debug(
                f"Initializing configuration using " +
                f"'{self._config_file}' configuration file")
        if access_key_id or secret_key:
            self._access_key_id = access_key_id
            self._secret_key = secret_key
        else:
            self._access_key_id = os.environ.get('ALERTLOGIC_ACCESS_KEY_ID')
            self._secret_key = os.environ.get('ALERTLOGIC_SECRET_KEY')

        self._global_endpoint = \
            global_endpoint or \
            os.environ.get('ALERTLOGIC_ENDPOINT')

        self._residency = \
            residency or \
            os.environ.get('ALERTLOGIC_RESIDENCY')

        self._account_id = \
            account_id or \
            os.environ.get('ALERTLOGIC_ACCOUNT_ID')

        self._profile = \
            profile or \
            os.environ.get('ALERTLOGIC_PROFILE') or \
            almdrlib.constants.DEFAULT_PROFILE

        self._parser = configparser.ConfigParser()
        if self._read_config_file():
            self._initialize_config()
        else:
            self._initialize_defaults()

        logger.debug(f"Finished configuraiton initialization. " +
                     f"access_key_id={self._access_key_id}, " +
                     f"account_id={account_id}, " +
                     f"global_endpoint={self._global_endpoint}")

    def _read_config_file(self):
        try:
            read_ok = self._parser.read(self._config_file)
            return False if self._config_file not in read_ok else True
        except configparser.MissingSectionHeaderError:
            raise ConfigException(
                    f"Invalid format in file {self._config_file}")

    def _initialize_defaults(self):
        self._global_endpoint = \
            self._global_endpoint or \
            almdrlib.constants.DEFAULT_GLOBAL_ENDPOINT

        self._residency = \
            self._residency or \
            almdrlib.constants.DEFAULT_RESIDENCY

    def _initialize_config(self):
        if self._access_key_id is None or self._secret_key is None:
            self._access_key_id = self._get_config_option(
                                        'access_key_id',
                                        None)
            self._secret_key = self._get_config_option('secret_key', None)

        self._global_endpoint = \
            self._global_endpoint or self._get_config_option(
                'global_endpoint',
                almdrlib.constants.DEFAULT_GLOBAL_ENDPOINT)

        self._residency = \
            self._residency or \
            self._get_config_option(
                'residency',
                almdrlib.constants.DEFAULT_RESIDENCY)

        self._account_id = \
            self._account_id or self._get_config_option('account_id', None)

    def _get_config_option(self, option_name, default_value):
        if self._parser.has_option(self._profile, option_name):
            return self._parser.get(self._profile, option_name)
        else:
            return default_value

    def get_auth(self):
        return self._access_key_id, self._secret_key

    @property
    def profile(self):
        return self._profile

    @property
    def account_id(self):
        return self._account_id

    @property
    def global_endpoint(self):
        return self._global_endpoint

    @property
    def residency(self):
        return self._residency

    @staticmethod
    def get_api_dir():
        api_dir = os.environ.get('ALERTLOGIC_API')
        return api_dir and f"{api_dir}" or f"{os.path.dirname(__file__)}/apis"
