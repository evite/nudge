#
# Copyright (C) 2011 Evite LLC

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
import logging as _log
import re

__admin = None


def set_admin(_admin):
    global __admin
    __admin = _admin


def get_admin():
    global __admin
    return __admin


class Admin(object):
    """
    NOTE: Add an endpoint sanity check wrapper.
    """
    def __init__(self, service_publisher):
        self.sp = service_publisher

        # Flag that the ServicePublisher checks to see if it should record a req or not.
        self.is_recording = False
        # Object to hold all the requests
        self.records = {}
        # Flag that the ServicePublisher checks to see if it should record this endpoint call for API coverage uses
        self.is_recording_endpoint_coverage = False
        # Object to hold the API coverage data
        self.api_calls = {}

        # Build list of possible API endpoints so we can match real endpoint calls to the regexes of the defined
        # endpoints.
        self.api_regexes = self.build_api_endpoint_regex_list()

    def build_api_endpoint_regex_list(self):
        compiled_uri_regexes = []
        for endpoint in sorted(self.sp._endpoints):
            compiled_uri_regexes.append({'uri': endpoint.uris, 'regexes': endpoint.regexs})
        return compiled_uri_regexes

    def start_recording(self):
        self.is_recording = True

    def stop_endpoint_coverage_recording(self):
        self.is_recording_endpoint_coverage = False

    def start_endpoint_coverage_recording(self):
        self.is_recording_endpoint_coverage = True

    def find_matching_uri(self, path):
        for entry in self.api_regexes:
            for regex in entry['regexes']:
                if regex.search(path):
                    return entry['uri']

    def update_api_coverage_for_endpoint(self, environ):
        '''
        This call keeps track of statistics for endpoint calls so we can build a report on API coverage later.
        '''

        # Do we have this endpoint in our list yet? If not, add it, otherwise update it's statistics.
        path = environ['PATH_INFO']
        uri = self.find_matching_uri(path)
        if not uri:
            _log.warn('No uri found for path (%s) with method (%s)' % (path, environ['REQUEST_METHOD']))
            return

        if path in self.api_calls:
            # Update the statistics for the endpoint
            self.api_calls[uri]['count'] += 1
        else:
            # Create statistics for the endpoint
            self.api_calls[uri] = {
                    'query string': environ['QUERY_STRING'],
                    'count': 1,
                    }

    def stop_recording(self, filter_function=None):
        self.is_recording = False
        if filter_function and callable(filter_function):
            self.records = filter_function(self.records)
        return self.records

    def clear_recording(self):
        self.records = {}

    def _start_req(self, req_id, wsgi_env, req_body):
        """
        Called by ServicePublisher to record the environment of a request.
        """
        self.records[req_id] = {'wsgi_env':wsgi_env, 'wsgi_req_body':req_body}

    def _stop_req(self, req_id, content, status_code, headers):
        """
        Called by ServicePublisher to record the environment associated with a response.
        """
                'status_code': status_code,
                'resp_body': content})
        else:
            _log.warn("Tried to record a response for a non-existent request.")
