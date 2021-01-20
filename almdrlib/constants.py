# -*- coding: utf-8 -*-

import os.path

DEFAULT_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".alertlogic")
DEFAULT_CONFIG_FILE = os.path.join(DEFAULT_CONFIG_DIR, "config")
DEFAULT_CREDENTIALS_FILE = os.path.join(DEFAULT_CONFIG_DIR, "credentials")
DEFAULT_PROFILE = "default"
DEFAULT_GLOBAL_ENDPOINT = "production"
DEFAULT_ENDPOINT_MAP_FILE = "endpoint_map.json"
DEFAULT_RESIDENCY = "default"
DEFAULT_SERVICE_NAME = "almdrlib"
