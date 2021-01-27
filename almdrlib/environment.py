'''Cloud stored environment configuration
AlEnv class implements retrieval and formatting of configuration parameters from dynamodb in the standardized way.
AWS client used is configured as follows https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html
Therefore, AWS cli configuration would be automatically picked up.
The simpliest way is to use environment variables.
Alert Logic specific configuration is done via ALERTLOGIC_STACK_REGION and ALERTLOGIC_STACK_NAME env variables.

Exceptions:
AlEnvException is a generic type for any AlEnv specific errors, derivatives are:
AlEnvConfigurationTableUnavailableException() - thrown when configuration table is not found
AlEnvAwsConfigurationException() - AWS credentials or configuration issue

Network or io errors are not handled.

Usage:
# export ALERTLOGIC_STACK_REGION=us-east-1
# export ALERTLOGIC_STACK_NAME=integration
>> env = AlEnv("myapplication")
# Assuming parameter is stored in ddb as '"value"'
>> env.get("my_parameter")
'value'
>> env.get("my_parameter", format='raw')
'"value"'
# Assuming parameter is stored in ddb as '"1.0"'
>> env.get("my_parameter", type='float')
1.0
>> env.get("my_parameter", type='integer')
1
# Assuming parameter is stored in ddb as '"true"'
>> env.get("my_parameter", type='boolean')
True
'''

import json
import boto3
import os
import botocore


class AlEnvException(Exception):
    pass


class AlEnvAwsConfigurationException(AlEnvException):
    pass


class AlEnvConfigurationTableUnavailableException(AlEnvException):
    pass


class AlEnv:
    def __init__(self, application_name):
        self.application_name = application_name
        self.region = AlEnv._get_region()
        self.stack_name = AlEnv._get_stack_name()
        self.table_name = AlEnv._table_name(self.region, self.stack_name)
        try:
            self.dynamodb = boto3.resource('dynamodb')
            self.table = self.dynamodb.Table(self.table_name)
            self._table_date_time = self.table.creation_date_time
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                raise AlEnvConfigurationTableUnavailableException(self.table_name)
            else:
                raise AlEnvException(e)
        except (botocore.exceptions.NoRegionError, botocore.exceptions.NoCredentialsError) as e:
            raise AlEnvAwsConfigurationException(f'Please validate your AWS configuration: {e}')

    def get(self, key, default=None, format='decoded', type=None):
        fetched_value = self.table.get_item(Key={"key": self._make_ddb_key(key)}).get('Item', {}).get('value')
        converted = AlEnv._convert(fetched_value, format, type)
        if converted is not None:
            return converted
        else:
            return default

    def _make_ddb_key(self, option_key):
        return f"{self.application_name}.{option_key}"

    @staticmethod
    def _convert(value, format, type):
        if format == 'raw' and value:
            return AlEnv._format_value(value, type)
        elif format == 'decoded' and value:
            decoded = json.loads(value)
            return AlEnv._format_value(decoded, type)
        else:
            return None

    @staticmethod
    def _format_value(value, type):
        if type == 'integer':
            return int(value)
        elif type == 'float':
            return float(value)
        elif type in ['boolean', 'bool']:
            return AlEnv._to_bool(value)
        else:
            return value

    @staticmethod
    def _to_bool(value):
        if isinstance(value, bool):
            return value
        elif value == 'true':
            return True
        elif value == 'false':
            return False
        else:
            raise ValueError('Provided value cannot be converted to boolean')

    @staticmethod
    def _table_name(region, stack_name):
        global_app = "global"
        config_table = "settings"
        environment_name = 'dev'
        return f"{region}.{stack_name}.{environment_name}.{global_app}.{config_table}"

    @staticmethod
    def _get_region():
        return os.environ.get('ALERTLOGIC_STACK_REGION', 'us-east-1')

    @staticmethod
    def _get_stack_name():
        return os.environ.get('ALERTLOGIC_STACK_NAME', 'integration')
