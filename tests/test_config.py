import unittest
from almdrlib.session import Session
import re

MOCK_AUTH = {
    "authentication": {
        "user": {
            "id": "589B64BB-AE91-4FA9-A6D8-37AC6759BB5D",
            "account_id": "2",
            "created": {
                "at": 1443713420,
                "by": "693BA145-78C0-4C77-AC1A-5385461839CD"
            },
            "modified": {
                "at": 1610707251,
                "by": "system"
            }
        },
        "account": {
            "id": "2",
            "name": "Alert Logic, Inc."
        },
        "token": "123",
    }
}


class NameSpace:
    def __init__(self, **kwargs):
        self.__dict__ = kwargs


class MockResponse():
    elapsed = NameSpace(total_seconds=lambda: 123)

    def __init__(self, code_body):
        (self.code, self.body) = code_body

    def json(self):
        return self.body

    def status_code(self):
        return self.code

    def raise_for_status(self):
        return None


class MockSession():
    def __init__(self, map):
        self.map = map

    def post(self, url):
        return MockResponse(self.get_status_body(url))

    def request(self, method, url, **kwargs):
        print("URL", url)
        return MockResponse(self.get_status_body(url))

    def get_status_body(self, url):
        for k, v in self.map.items():
            if re.match(k, url):
                return v
        return 200, {}


class TestConf(unittest.TestCase):
    def test_globalep(self):
        session = Session(global_endpoint="http://api.aesolo.com:8100")
        assert session.get_url("aetuner", "1234567") == "http://api.aesolo.com:8100"
        session = Session(global_endpoint="production")
        session._session = MockSession({r".*aims/v1/authenticate":
                                            (200, MOCK_AUTH),
                                        r".*residency/default/services/aetuner/endpoint":
                                            (200, {"aetuner":"api.alertlogic.com"})})
        assert session.get_url("aetuner", "1234567") == "https://api.alertlogic.com"


if __name__ == '__main__':
    unittest.main()
