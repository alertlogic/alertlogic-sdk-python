# -*- coding: utf-8 -*-

import almdrlib
import datetime
import logging
from time import sleep

"""
    almdrlib.search
    ~~~~~~~~~~~~~~~
    Wrapper around search API to support submit/execute workflow
"""

SEARCH_TYPE = 'batch'   # complete searches vs. return first results quickly
ROWS_PER_FETCH = 10000  # per request to get search results


def iso_to_epoch(t):
    '''covert iso8601 time to POSIX/epoch timestamp'''
    return int(datetime.timestamp(datetime.fromisoformat(t)))


class Search():
    def __init__(self, session=None):
        if session:
            self.search_client = almdrlib.client('search', session=session)
        else:
            self.search_client = almdrlib.client('search')

        self.search_id = None
        self.logger = logging.getLogger(__name__)

    def submit(self, account_id, query_string,
               search_type=SEARCH_TYPE, timeframe=None, start=None, end=None):
        """submit
        Submit the query for execution."""

        if timeframe is not None:
            time_args = {'timeframe': timeframe}
        elif start is not None and end is not None:
            time_args = {'start': iso_to_epoch(args.start),
                         'end': iso_to_epoch(args.end)}
            # TODO support non-ISO
        else:
            raise Exception('Specify timeframe or stand and end')

        # POST search/v2/:account_id/searches?search_type=...
        # request body is the query
        response = self.search_client.start_query_execution(
            account_id=account_id, query_string=query_string,
            search_type=SEARCH_TYPE, **time_args)
        self.search_id = response.json()['search_uuid']
        self.next_token = None
        self.account_id = account_id
        self.remaining = None

        return self.search_id

    def fetch(self, block=True):
        # Ask for results for this query, and process a single batch

        while True:
            # GET search/v2/:account_id/searches/:search_id/status
            response = self.search_client.get_search_status(
                account_id=self.account_id, search_uuid=self.search_id)

            status = response.json()
            search_status = status['search_status']
            self.logger.debug(f'Search status for {self.search_id} is {search_status}')

            # pending: no results yet
            if search_status == 'pending':
                search_progress = status.get('search_progress')
                if search_progress is not None:
                    self.progress = status['progress']
                    self.records = search_progress['input_scanned_records']
                    self.bytes = search_progress['input_scanned_bytes']
                    self.estimated_results = search_progress['estimated_output_records']
                    self.logger.debug(f'Search progress {self.progress}%: {self.records} '
                                      f'records, {self.bytes} bytes, {self.estimated_results} output')

                if not block:
                    return None
                else:
                    sleep(1)

            # failed: syntax errors, runtime problems, etc.
            elif search_status == 'failed':
                raise Exception(f'Search {search_id} failed: {status}')

            # suspended or completed: some or all results available (respectively)
            elif search_status in ['complete', 'suspended']:
                # GET search/v2/:account_id/searches/:search_id?limit=...
                if self.next_token is None:
                    self.logger.debug(f'Fetching initial results for {self.search_id}')
                    response = self.search_client.get_search_results(
                        account_id=self.account_id, search_uuid=self.search_id,
                        limit=ROWS_PER_FETCH)
                else:
                    self.logger.debug(f'Fetching next page of results for {self.search_id} '
                                      f'with token {self.next_token}')
                    response = self.search_client.get_search_results(
                        account_id=self.account_id, search_uuid=self.search_id,
                        starting_token=self.next_token)
                results = response.json()
                self.remaining = results['remaining']
                self.logger.debug(f'{self.remaining} remaining results for {self.search_id}')

                if self.remaining != 0:
                    # advance to the next page of results on the next query
                    self.next_token = results['next_token']
                self.logger.debug(results)
                return results['results']['records']

    def results_remaining(self):
        return self.remaining is None or self.remaining > 0

    def fetch_all(self):
        # Ask for results for this query, and process all batches

        results = []
        while self.results_remaining():
            results += self.fetch(block=True)
        return results
