import unittest
from unittest.mock import MagicMock
from almdrlib.environment import AlEnv, AlmdrlibSourceNotEnabledError
import os
import boto3


class MockDDBTable:
    creation_date_time = '2005-08-09T18:31:42-03:30'
    def __init__(self, tablename):
        pass

    def get_item(self, **kwargs):
        Key = kwargs.get('Key')['key']
        if Key == 'someapplication.strkey':
            return {"Item": {"key": Key, "value": "\"strvalue\""}}
        elif Key == 'someapplication.intkey':
            return {"Item": {"key": Key, "value": "\"1\""}}
        elif Key == 'someapplication.floatkey':
            return {"Item": {"key": Key, "value": "\"1.0\""}}
        elif Key == 'someapplication.boolkeytrue':
            return {"Item": {"key": Key, "value": "\"true\""}}
        elif Key == 'someapplication.boolkeyfalse':
            return {"Item": {"key": Key, "value": "\"false\""}}
        elif Key == 'otherapplication.authc.strkey':
            return {"Item": {"key": Key, "value": "\"strvalue\""}} 


class MockBotoDDB:
    Table = MockDDBTable

    def __init__(self, client_type):
        pass

class SSMExceptions:

    class ParameterNotFound(Exception):
        pass

class MockBotoSSM:

    exceptions = SSMExceptions()

    def __init__(self, client_type):
        pass

    @staticmethod
    def get_parameter(**kwargs):
        Name = kwargs.get('Name')
        WithDecryption = kwargs.get('WithDecryption')

        if Name == '/deployments/production/us-west-1/env-settings/someapplication/stringparam':
            return {'Parameter': {'Value': 'testingtesting'}}
        elif Name == '/deployments/production/us-west-1/env-settings/someapplication/securestringparam':
            if WithDecryption:
                return {'Parameter': {'Value': 'testingtestingtesting'}}
            else:
                return {'Parameter': {'Value': 'AQICAHhxjBnL9Dhpl/8CUT7/NC07HUYnX+P'}}
        elif Name == '/deployments/production/us-west-1/env-settings/otherapplication/authc.stringparam':
            return {'Parameter': {'Value': 'testingtesting'}}
        else:
            raise MockBotoSSM.exceptions.ParameterNotFound()


class TestAlEnv(unittest.TestCase):
    def test_something(self):
        boto3.resource = MagicMock(return_value=MockBotoDDB)
        boto3.client = MagicMock(return_value=MockBotoSSM)
        os.environ['ALERTLOGIC_STACK_REGION'] = 'us-west-1'
        os.environ['ALERTLOGIC_STACK_NAME'] = 'production'
        env = AlEnv("someapplication", source="dynamodb")
        assert env.table_name == 'us-west-1.production.dev.global.settings'
        assert env.get("strkey") == 'strvalue'
        assert env.get("strkey", format='raw') == '"strvalue"'
        assert env.get("intkey") == '1'
        assert env.get("intkey", type='float') == 1.0
        assert env.get("boolkeyfalse") == 'false'
        assert env.get("boolkeyfalse", type='boolean') is False
        assert env.get("boolkeytrue", type='boolean') is True
        assert env.get("floatkey") == '1.0'
        assert env.get("floatkey", type='float') == 1.0
        with self.assertRaises(AlmdrlibSourceNotEnabledError):
            assert env.get_parameter("testparam")    
        env = AlEnv("otherapplication", "authc", source="dynamodb")
        assert env.get("strkey") == 'strvalue'

        env = AlEnv("someapplication", source="ssm")
        assert env.get_parameter("stringparam") == 'testingtesting'
        assert env.get_parameter("securestringparam") == 'AQICAHhxjBnL9Dhpl/8CUT7/NC07HUYnX+P'
        assert env.get_parameter("securestringparam", decrypt=False) == 'AQICAHhxjBnL9Dhpl/8CUT7/NC07HUYnX+P'
        assert env.get_parameter("securestringparam", decrypt=True) == 'testingtestingtesting'
        assert env.get_parameter("invalidparam", "default") == 'default'
        with self.assertRaises(AlmdrlibSourceNotEnabledError):
            assert env.get("testparam")    
        env = AlEnv("otherapplication", "authc", source="ssm")
        assert env.get_parameter("stringparam") == 'testingtesting'

        env = AlEnv("someapplication", source=("ssm", "dynamodb"))
        assert env.get("strkey") == 'strvalue'
        assert env.get_parameter("stringparam") == 'testingtesting'


if __name__ == '__main__':
    unittest.main()
