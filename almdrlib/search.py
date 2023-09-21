# -*- coding: utf-8 -*-

import time
import almdrlib
from datetime import datetime
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


def local_tz_offset():
    '''approximate a GMT offset'''
    offset = -time.timezone  # -3600 = +01:00

    hours = int(offset / 3600)
    minutes = int((offset - hours*3600) / 60)
    return "{:+03d}:{:02d}".format(hours, minutes)


def resolve_time(start_ts=None, end_ts=None,
                 start=None, end=None,
                 timeframe=None):
    '''resolve_time
    returns arguments to be passed to search as a time range. Prefer
    relative time over ISO time over timestamps'''
    if timeframe is not None:
        return {'timeframe': timeframe}
    elif start is not None and end is not None:
        return {'start': iso_to_epoch(start),
                'end': iso_to_epoch(end)}
    elif start_ts is not None and end_ts is not None:
        return {'start': start_ts, 'end': end_ts}
    else:
        raise Exception('Specify timeframe or stand and end')


class Search():
    def __init__(self, session=None):
        self.search_client = almdrlib.client('search', session=session)
        self.stylist_client = almdrlib.client('search_stylist', session=session)

        self.search_id = None
        self.logger = logging.getLogger(__name__)

    def submit_v1(self, account_id, query, datatype='logmsgs',
               search_type=SEARCH_TYPE, **timekwargs):
        """submit
        Submit V1 query for execution."""

        # XXX fetch_v1 needed, but doesn't really work.
        response = self.search_client.start_log_search_query_execution(
            account_id=account_id, query=query, datatype=datatype,
             **timekwargs)
        self.load_results(account_id, response.json()['search_uuid'])
        return self.search_id

    def submit(self, account_id, query_string,
               search_type=SEARCH_TYPE, **timekwargs):
        """submit
        Submit the query for execution."""

        time_args = resolve_time(**timekwargs)

        # POST search/v2/:account_id/searches?search_type=...
        # request body is the query
        response = self.search_client.start_query_execution(
            account_id=account_id, query_string=query_string,
            search_type=search_type, **time_args)
        self.load_results(account_id, response.json()['search_uuid'])

        return self.search_id

    def load_results(self, account_id, result_id):
        """load_results
        Attempt to load existing search results by ID"""
        self.search_id = result_id
        self.next_token = None
        self.account_id = account_id
        self.remaining = None

    def wait_for_complete(self, block=True) -> object:
        # Ask for results for this query, and process a single batch
        # TODO isolate polling form result fetching

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
                raise Exception(f'Search {self.search_id} failed: {status}')

            # suspended or completed: some or all results available (respectively)
            elif search_status in ['complete', 'suspended']:
                return True

    def fetch(self, block=True, rows=ROWS_PER_FETCH) -> dict:
        # Ask for results for this query, and process a single batch
        # TODO isolate polling form result fetching

        while True:
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
                raise Exception(f'Search {self.search_id} failed: {status}')

            # suspended or completed: some or all results available (respectively)
            elif search_status in ['complete', 'suspended']:
                # GET search/v2/:account_id/searches/:search_id?limit=...
                if self.next_token is None:
                    self.logger.debug(f'Fetching initial results for {self.search_id}')
                    response = self.search_client.get_search_results(
                        account_id=self.account_id, search_uuid=self.search_id,
                        limit=rows)
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
                return results

    def fetch_v1(self, block=True, rows=ROWS_PER_FETCH) -> dict:
        # XXX can't page through results, probably need to do math vs tokens
        while True:
            response = self.search_client.get_log_search_results(
                account_id=self.account_id, search_uuid=self.search_id)

            status = response.json()
            search_status = status['search_status']
            self.logger.debug(f'Search status for {self.search_id} is {search_status}')

            # pending: no results yet
            if search_status == 'pending':
                if not block:
                    return None
                else:
                    sleep(1)

            # failed: syntax errors, runtime problems, etc.
            elif search_status == 'failed':
                raise Exception(f'Search {self.search_id} failed: {status}')

            # suspended or completed: some or all results available (respectively)
            elif search_status in ['complete', 'suspended']:
                # GET search/v2/:account_id/searches/:search_id?limit=...
                if self.next_token is None:
                    results = status
                else:
                    self.logger.debug(f'Fetching next page of results for {self.search_id} '
                                      f'with token {self.next_token}')
                    response = self.search_client.get_log_search_results(
                        account_id=self.account_id, search_uuid=self.search_id,
                        starting_token=self.next_token)
                    results = response.json()
                self.remaining = results['remaining']
                self.logger.debug(f'{self.remaining} remaining results for {self.search_id}')

                if self.remaining != 0:
                    # advance to the next page of results on the next query
                    self.next_token = results['next_token']
                elif search_status == 'suspended':
                    self.remaining = 1
                # self.logger.debug(results)
                return results

    def results_remaining(self):
        return self.remaining is None or self.remaining > 0

    def fetch_all(self):
        # Ask for results for this query, and process all batches

        results = []
        while self.results_remaining():
            raw_results = self.fetch(block=True)
            results.append(raw_results)
        return results

    def export(self, format, utc_offset=None):
        self.wait_for_complete(block=True)
        awful = {"from_epochtime.utc_offset": utc_offset}
        out = self.stylist_client.export_transformed_search_results(
            account_id=self.account_id, search_uuid=self.search_id,
            result_format=format, **awful)

        return out.text
