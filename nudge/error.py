#!/usr/bin/env python
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA
import inspect
import logging
import nudge.json

_log = logging.getLogger("nudge.error")

__all__ = [
    'responses',
    'HTTPException',
    'JsonErrorHandler',
    'handle_exception',
]
DEFAULT_ERROR_CODE = 500
DEFAULT_ERROR_CONTENT_TYPE = "application/json; charset=UTF-8"
DEFAULT_ERROR_CONTENT = '{"message": "%s", "code": %i}' % (
    "Internal Server Error",
    DEFAULT_ERROR_CODE,
)
responses = {
  100: 'Continue',
  101: 'Switching Protocols',

  200: 'OK',
  201: 'Created',
  202: 'Accepted',
  203: 'Non-Authoritative Information',
  204: 'No Content',
  205: 'Reset Content',
  206: 'Partial Content',

  300: 'Multiple Choices',
  301: 'Moved Permanently',
  302: 'Found',
  303: 'See Other',
  304: 'Not Modified',
  305: 'Use Proxy',
  306: '(Unused)',
  307: 'Temporary Redirect',

  400: 'Bad Request',
  401: 'Unauthorized',
  402: 'Payment Required',
  403: 'Forbidden',
  404: 'Not Found',
  405: 'Method Not Allowed',
  406: 'Not Acceptable',
  407: 'Proxy Authentication Required',
  408: 'Request Timeout',
  409: 'Conflict',
  410: 'Gone',
  411: 'Length Required',
  412: 'Precondition Failed',
  413: 'Request Entity Too Large',
  414: 'Request-URI Too Long',
  415: 'Unsupported Media Type',
  416: 'Requested Range Not Satisfiable',
  417: 'Expectation Failed',
  418: 'I\'m a teapot',

  500: 'Internal Server Error',
  501: 'Not Implemented',
  502: 'Bad Gateway',
  503: 'Service Unavailable',
  504: 'Gateway Timeout',
  505: 'HTTP Version Not Supported',
}

class JsonErrorHandler(object):
    """ Default nudge error handler.
        If Nudge catches an HTTPException, we will try to set the code 
        from that exception. AssertionErrors are considered normal
        bad request errors, and 400 is returned. Otherwise this returns
        500 with {code:500 , message:message} where message is the exception
        message. """
    code = DEFAULT_ERROR_CODE
    content_type = DEFAULT_ERROR_CONTENT_TYPE
    content = DEFAULT_ERROR_CONTENT
    headers = {}
    def __call__(self, exp):
        code = self.code
        message = exp.message
        if isinstance(exp, HTTPException):
            code = exp.status_code
            if not message:
                message = responses[code]
        elif isinstance(exp, AssertionError):
            code = 400
            message = exp.message
            _log.debug("Assertion error: %s", exp.message)
        else:
            message = responses[DEFAULT_ERROR_CODE]
            _log.exception("Exception handled by JsonErrorHandler")
        # TODO (maybe) add the rest of the exceptions members to the resp
        content = {'message': message, 'code':code}
        return code, self.content_type, \
            nudge.json.json_encode(content), self.headers

def handle_exception(exp, exp_handlers):
    # Check if this endpoint can handle this exception
    if exp_handlers:
        exps = inspect.getmro(exp.__class__)
        exp_class = None

        for clazz in exps:
            if clazz in exp_handlers:
                exp_class = clazz
                break

        if exp_class:
            exp_handler = exp_handlers[exp_class]
            if callable(exp_handler):
                # TODO maybe give e the req and start response, maybe add
                # a finished var to track if e handled everything
                return exp_handler(exp)
            else:
                # Handle 'simple' tuple based exception handler (not callable)
                return (exp_handler.code, exp_handler.content_type,
                        exp_handler.content, exp_handler.headers)

    _log.exception("Unhandled exception class: %s", exp.__class__)
    raise exp

class HTTPException(Exception):

    def __init__(self, status_code, message=None):
        self.status_code = status_code
        self.message = message

