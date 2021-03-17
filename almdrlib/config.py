# -*- coding: utf-8 -*-

import os.path
import configparser
import logging
import json
import almdrlib.constants
from almdrlib.exceptions import AlmdrlibValueError
from almdrlib.environment import AlEnv

logger = logging.getLogger(__name__)


class ConfigException(Exception):
    def __init__(self, message):
        super(ConfigException, self).__init__("config error: {message}")


class Config():
    """
    Reads configuration parameters from either environment variables
        or from configuration file

    Environment Variables:
    ALERTLOGIC_CONFIG - Location of the configuration file. If not specified,
    ~/.alertlogic/credentials is used
    ALERTLOGIC_PROFILE - Profile to be used.
    If not specified [default] section is used
    ALERTLOGIC_ACCESS_KEY_ID - Access Key Id
    ALERTLOGIC_SECRET_KEY - Secret Key
    ALERTLOGIC_ENDPOINT - endpoint id: production | integration, a map, or a url are the supported values
    ALERTLOGIC_ENDPOINT_MAP - (full or relative to config directory) path of a json file mapping services to endpoints
    ALERTLOGIC_ACCOUNT_ID - Account Id to perform operations against.
    ALERTLOGIC_RESIDENCY - Data Residency when creating new deployments
    ALERTLOGIC_API  - Directory where OpenAPI yaml files reside
    ALERTLOGIC_SERVICE_NAME - If a (micro)service is built around almdrlib used as identifier

    Config File section values
    access_key_id - User's AIMS Access Key ID
    secret_key - Secret Key associated with 'access_key_id'
    global_endpoint - if not specified, 'production' endpoint is used
    endpoint_map_file - if not specified, 'endpoint_map.json' in the config directory (default: ~/.alertlogic) is used
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
                 endpoint_map_file=None,
                 residency=None,
                 service_name=None):
        self._config_file = os.environ.get('ALERTLOGIC_CONFIG')
        self._endpoint_map = None
        self._service_name = service_name

        if self._config_file is None:
            self._config_file = almdrlib.constants.DEFAULT_CONFIG_FILE

        logger.debug(
                "Initializing configuration using " +
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

        self._endpoint_map_file = \
            endpoint_map_file or \
            os.environ.get('ALERTLOGIC_ENDPOINT_MAP')

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

        self._service_name = \
            service_name or \
            os.environ.get('ALERTLOGIC_SERVICE_NAME') or \
            almdrlib.constants.DEFAULT_SERVICE_NAME

        self._parser = configparser.ConfigParser()
        if self._read_config_file():
            self._initialize_config()
        else:
            self._initialize_defaults()

        self._init_al_env_credentials(service_name)

        logger.debug("Finished configuraiton initialization. " +
                     f"access_key_id={self._access_key_id}, " +
                     f"account_id={self._account_id}, " +
                     f"global_endpoint={self._global_endpoint}")

    def _init_al_env_credentials(self, service_name):
        try:
            if self._access_key_id is None or self._secret_key is None:
                service_name_key = f"{service_name}.aims_authc",
                env = AlEnv(service_name_key)
                self._access_key_id = env.get('access_key_id')
                self._secret_key = env.get('secret_access_key')
        except Exception as e:
            logger.debug(f"Did not initialise aims credentials for {service_name} because {e}")

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
            self._access_key_id = self._get_config_option('access_key_id', None)
            self._secret_key = self._get_config_option('secret_key', None)

        self._global_endpoint = \
            self._global_endpoint or self._get_config_option(
                'global_endpoint',
                almdrlib.constants.DEFAULT_GLOBAL_ENDPOINT)

        self._endpoint_map_file = \
            self._endpoint_map_file or self._get_config_option(
                'endpoint_map_file',
                almdrlib.constants.DEFAULT_ENDPOINT_MAP_FILE)
        self._endpoint_map_file = \
            self._endpoint_map_file or \
            almdrlib.constants.DEFAULT_ENDPOINT_MAP_FILE

        if self._global_endpoint == "map":
            if os.path.isabs(self._endpoint_map_file):
                path = self._endpoint_map_file
            else:
                path = os.path.join(almdrlib.constants.DEFAULT_CONFIG_DIR, self._endpoint_map_file)
            with open(path) as json_file:
                self._endpoint_map = json.load(json_file)

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

    @staticmethod
    def configure(
            profile=almdrlib.constants.DEFAULT_PROFILE,
            account_id=None,
            access_key_id=None, secret_key=None,
            global_endpoint=None,
            endpoint_map_file=None,
            residency=None):

        if not access_key_id:
            raise AlmdrlibValueError("Missing access_key_id")

        if not secret_key:
            raise AlmdrlibValueError("Missing secret_key")

        parser = _get_config_parser(almdrlib.constants.DEFAULT_CONFIG_FILE)

        try:
            parser.add_section(profile)
        except configparser.DuplicateSectionError:
            # section alread exists.
            pass
        except configparser.ValueError:
            # almdrlib.constants.DEFAULT_PROFILE was passed as the section name
            pass

        parser.set(profile, 'access_key_id', access_key_id)
        parser.set(profile, 'secret_key', secret_key)

        if account_id:
            parser.set(profile, 'account_id', account_id)

        if global_endpoint:
            parser.set(profile, 'global_endpoint', global_endpoint)

        if endpoint_map_file:
            parser.set(profile, 'endpoint_map_file', endpoint_map_file)

        if residency:
            parser.set(profile, 'residency', residency)

        with open(almdrlib.constants.DEFAULT_CONFIG_FILE, 'w') as configfile:
            parser.write(configfile)

    @staticmethod
    def set_option(
            name,
            value,
            profile=almdrlib.constants.DEFAULT_PROFILE):
        parser = _get_config_parser(almdrlib.constants.DEFAULT_CONFIG_FILE)
        parser.set(profile, name, value)
        with open(almdrlib.constants.DEFAULT_CONFIG_FILE, 'w') as configfile:
            parser.write(configfile)

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
    def endpoint_map(self):
        return self._endpoint_map

    @property
    def residency(self):
        return self._residency

    @staticmethod
    def get_api_dir():
        api_dir = os.environ.get('ALERTLOGIC_API')
        return api_dir and f"{api_dir}"


def _get_config_parser(config_file=almdrlib.constants.DEFAULT_CONFIG_FILE):
    parser = configparser.ConfigParser()
    try:
        read_ok = parser.read(config_file)
        if config_file not in read_ok:
            raise AlmdrlibValueError(
                f"'{config_file}' doesn't exist")

    except configparser.MissingSectionHeaderError:
        raise ConfigException(
                f"Invalid format in file {config_file}")
    return parser
