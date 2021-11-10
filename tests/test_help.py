#!/usr/bin/env python

import almdrlib
import os
import json
import inspect

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

    def test_000_get_signature(self):
        """Test the signature for test_get_data."""
        client = almdrlib.client('testapi')
        test_get_data_sig = inspect.Signature([
            inspect.Parameter('header_param1', inspect.Parameter.KEYWORD_ONLY, annotation=str),
            inspect.Parameter('query_param1', inspect.Parameter.KEYWORD_ONLY, annotation=str),
            inspect.Parameter('account_id', inspect.Parameter.KEYWORD_ONLY, annotation=str, default='2'),
            inspect.Parameter('header_param2', inspect.Parameter.KEYWORD_ONLY, annotation=int),
            inspect.Parameter('query_param2', inspect.Parameter.KEYWORD_ONLY, annotation=list),
            inspect.Parameter('query_param3', inspect.Parameter.KEYWORD_ONLY, annotation=dict),
        ])
        self.assertEqual(test_get_data_sig, client.test_get_data.__signature__)

    def test_001_post_signature(self):
        """Test the signature for post_payload_in_body."""
        client = almdrlib.client('testapi')
        post_payload_in_body_sig = inspect.Signature([
            inspect.Parameter('account_id', inspect.Parameter.KEYWORD_ONLY, annotation=str, default='2'),
            inspect.Parameter('payload', inspect.Parameter.KEYWORD_ONLY),
            inspect.Parameter('content_type', inspect.Parameter.KEYWORD_ONLY, annotation=str, default='application/json')
        ])
        self.assertEqual(post_payload_in_body_sig, client.post_payload_in_body.__signature__)

    def test_002_doc_body(self):
        """Validate that the description is somewhere in the documentation."""
        client = almdrlib.client('testapi')
        self.assertIn(client.test_get_data.description, client.test_get_data.__doc__)
