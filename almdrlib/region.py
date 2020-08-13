# -*- coding: utf-8 -*-

from enum import Enum

"""
    alertlogic.region
    ~~~~~~~~~~~~~~
    alertlogic region management
"""
"""
List of known regions
"""
ENDPOINTS = {
    "production": "https://api.global-services.global.alertlogic.com",
    "integration": "https://api.global-integration.product.dev.alertlogic.com"
}


class NoValue(Enum):
    def __repr__(self):
        return '<%s.%s>' % (self.__class__.__name__, self.name)


class Residency(NoValue):
    @staticmethod
    def list_residencies():
        return ['default', 'us', 'emea']

    DEFAULT = 'default'
    US = 'us'
    EMEA = 'emea'


class EndpointType(NoValue):
    API = 'api'
    UI = 'ui'


class Region():
    """
    Abstracts an alertlogic region.
    For now it only represents the api endpoint url
    """

    def __init__(self):
        pass

    @staticmethod
    def list_endpoints():
        return ENDPOINTS.keys()

    @staticmethod
    def get_global_endpoint(endpoint):
        return ENDPOINTS.get(endpoint, endpoint)

    @staticmethod
    def get_region_from_location(location):
        return location.split('-')[1]

    @staticmethod
    def get_endpoint_url(url, service_name, account_id, residency="default"):
        return "{}/endpoints/v1/{}/residency/{}/services/{}/endpoint".format(
                url,
                account_id,
                residency,
                service_name)
