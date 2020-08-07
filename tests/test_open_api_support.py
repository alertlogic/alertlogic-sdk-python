#!/usr/bin/env python
import os
import json

"""Tests for `alertlogic-sdk-python` package."""

import unittest

from almdrlib.session import Session
from almdrlib.client import Client
from almdrlib.client import Config
from almdrlib.client import Operation
from alsdkdefs import OpenAPIKeyWord


class TestSdk_open_api_support(unittest.TestCase):
    """Tests for `python_boilerplate` package."""

    def setUp(self):
        """Set up test fixtures, if any."""
        dir_path = os.path.dirname(os.path.realpath(__file__))
        os.environ["ALERTLOGIC_API"] = f"{dir_path}/apis"
        self._service_name = "testapi"

        test_data_file = None
        test_data_file_path = f"{dir_path}/data/test_open_api_support.json"
        with open(test_data_file_path, "r") as value_file:
            test_data_file = value_file.read()

        self.test_data = json.loads(test_data_file)

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_000_getting_schemas(self):
        """Test listing services."""
        self.assertTrue(len(Session.get_service_api("testapi")))
        print(f"SCHEMA: {json.dumps(Session.get_service_api('testapi'))}")

    def test_001_test_client_initialization(self):
        """Test OpenAPI Client initialization."""
        client = Client(self._service_name)
        self.assertIsInstance(client, Client)
        self.assertIsNotNone(client.description)
        self.assertNotEqual(client.name, "")
        self.assertIsNotNone(client.server)
        self.assertNotEqual(client.info, {})
        self.assertIsNotNone(client.operations)
        self.assertNotEqual(client.spec, {})
        self.assertNotEqual(client.operations, {})

    def test_002_test_operations_schema(self):
        """Test Operations Schema Validity."""
        client = Client(self._service_name)

        for t_operation_name, t_operation_schema in \
                self.test_data['operations'].items():
            operation = client.operations.get(t_operation_name)
            self.assertIsInstance(operation, Operation)
            self.assertEqual(operation.operation_id, t_operation_name)
            self.assertEqual(operation.description,
                             t_operation_schema[OpenAPIKeyWord.DESCRIPTION])

            schema = operation.get_schema()
            self.assertIsNot(schema, {})

            t_operation_parameters = t_operation_schema[
                OpenAPIKeyWord.PARAMETERS]

            operation_parameters = schema[OpenAPIKeyWord.PARAMETERS]
            for name, value in t_operation_parameters.items():
                self.assertEqual(value, operation_parameters[name])

            if OpenAPIKeyWord.CONTENT in t_operation_schema:
                t_operation_content = t_operation_schema[
                    OpenAPIKeyWord.CONTENT]
                operation_content = schema[OpenAPIKeyWord.CONTENT]
                for name, value in t_operation_content.items():
                    self.assertEqual(value, operation_content[name])

    def test_003_default_objects_creation(self):
        """Checks initialisation at least happens"""
        self.assertIsInstance(Session(), Session)
        self.assertIsInstance(Config(), Config)
        self.assertIsInstance(Client(self._service_name), Client)
