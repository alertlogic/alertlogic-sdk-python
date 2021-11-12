#!/usr/bin/env python

import almdrlib
import os
import inspect

"""Tests for `alertlogic-sdk-python` package."""

import unittest


class TestSdk_open_api_support(unittest.TestCase):
    """Tests for documentation generation."""

    def setUp(self):
        """Set up test fixtures, if any."""
        dir_path = os.path.dirname(os.path.realpath(__file__))
        os.environ["ALERTLOGIC_API"] = f"{dir_path}/apis"
        self._service_name = "testapi"
        self._account_id = '2'
        self._session = almdrlib.session.Session(account_id=self._account_id, global_endpoint='https://example.net')

    def test_000_get_signature(self):
        """Test the signature for test_get_data."""
        client = almdrlib.client('testapi', session=self._session)
        # Order matters - path paramters first (account_id), then query params, then header params.
        # AlertLogic doesn't use Cookie parameters generally, but they'd be last.
        test_get_data_sig = inspect.Signature([
            inspect.Parameter('account_id', inspect.Parameter.KEYWORD_ONLY, annotation=str, default=self._account_id),
            inspect.Parameter('query_param1', inspect.Parameter.KEYWORD_ONLY, annotation=str),
            inspect.Parameter('query_param2', inspect.Parameter.KEYWORD_ONLY, annotation=list),
            inspect.Parameter('query_param3', inspect.Parameter.KEYWORD_ONLY, annotation=dict),
            inspect.Parameter('header_param1', inspect.Parameter.KEYWORD_ONLY, annotation=str),
            inspect.Parameter('header_param2', inspect.Parameter.KEYWORD_ONLY, annotation=int),
        ])
        self.assertEqual(test_get_data_sig, client.test_get_data.__signature__)

    def test_001_post_signature(self):
        """Test the signature for post_payload_in_body."""
        client = almdrlib.client('testapi', session=self._session)
        post_payload_in_body_sig = inspect.Signature([
            inspect.Parameter('account_id', inspect.Parameter.KEYWORD_ONLY, annotation=str, default=self._account_id),
            inspect.Parameter('content_type', inspect.Parameter.KEYWORD_ONLY, annotation=str, default='application/json'),
            inspect.Parameter('payload', inspect.Parameter.KEYWORD_ONLY),
        ])
        self.assertEqual(post_payload_in_body_sig, client.post_payload_in_body.__signature__)

    def test_002_doc_body(self):
        """Validate that the description is somewhere in the documentation."""
        client = almdrlib.client('testapi', session=self._session)
        self.assertIn(client.test_get_data.description, client.test_get_data.__doc__)
