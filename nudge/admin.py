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

from pprint import pformat
import logging as _log

__admin = None

def set_admin(_admin):
    global __admin
    __admin = _admin

def get_admin():
    global __admin
    return __admin

class Admin(object):
    def __init__(self, service_publisher):
        self.sp = service_publisher

        # Flag that the ServicePublisher checks to see if it should record a req or not.
        self.is_recording = False
        # Object to hold all the requests
        self.records = {}

    def start_recording(self):
        self.is_recording = True

    def stop_recording(self):
        self.is_recording = False
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
        if req_id  in self.records:
            self.records[req_id].update({'resp_headers':headers, 'status_code':status_code, 'resp_body':content})
        else:
            _log.warn("Tried to record a response for a non-existent request.")