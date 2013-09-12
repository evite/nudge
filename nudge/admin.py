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

import cStringIO
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
    # We have started recording requests
    is_recording = False
    # Object to hold all the requests
    requests = None

    def __init__(self, service_publisher):
        self.sp = service_publisher

    def start_record(self):
        pass

    def stop_record(self):
        pass

    # Called from SP
    def _start_req(self, wsgi_env):
        # NOTE we need to restore the request body after we read it.
        req_body = wsgi_env['wsgi.input'].getvalue()
        del wsgi_env['wsgi.input']
        _log.warn("*********************** Incoming request:")
        _log.warn("Got WSGI ENV:")
        _log.warn(pformat(wsgi_env))
        _log.warn("Got request body:")
        _log.warn(req_body)
        wsgi_env['wsgi.input'] = cStringIO.StringIO(req_body)

    def _stop_req(self, content, status_code, headers):
        _log.warn("\n*********************** Outgoing response:")
        _log.warn("Response content:")
        _log.warn(content)
        _log.warn("Status code (%i)", status_code)
        _log.warn("Headers: ")
        _log.warn(pformat(headers))


