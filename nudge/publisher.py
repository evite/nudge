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

import cgi
import logging
import re
import sys
import types
import time
import types
import urllib
import warnings

import nudge.json
import nudge.arg as args
from nudge.validator import ValidationError
from nudge.renderer import ExceptionRenderer
from nudge.json import Dictomatic

_log = logging.getLogger("nudge.servicepublisher")
_root_log = logging.getLogger("nudge")

__all__ = [
    'responses',
    'Args',
    'Endpoint',
    'WSGIRequest',
    'ServicePublisher',
    'HTTPException',
]

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

def lazyprop(fn):
    attr_name = '_lazy_' + fn.__name__
    @property
    def _lazyprop(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, fn(self))
        return getattr(self, attr_name)
    return _lazyprop


def Args(*args, **kwargs):
    return list(args) or [], kwargs or {}

class Endpoint(object):
    sequential = []
    named = {}

    def __init__(self, name=None, method=None, uri=None, function=None, 
                 args=None, exceptions=None, renderer=None):
        # Someday support unicode here, for now only bytestrings.
        assert isinstance(name, str)
        assert isinstance(method, str)
        assert isinstance(uri, str)
        assert callable(function), "function must be callable, but was %s" %\
            type(function)
        assert not exceptions or isinstance(exceptions, dict), \
            "exceptions must be a dict, but was type %s" % type(exceptions)
        if exceptions:
            for exception, error_code in exceptions.items():
                # Make sure it is a real Exception
                if not issubclass(exception, Exception):
                    raise TypeError(
                        "Endpoint exceptions must be subclasses of Exception "
                    )
                # Make sure the error_codes are valid. This may be too tightly
                # restricted.
                if not isinstance(error_code, int) or \
                        error_code not in responses:
                    raise TypeError(
                        "Invalid endpoint exception error code %s" \
                            % (error_code)
                    )
        if exceptions and renderer and isinstance(renderer, ExceptionRenderer):
            warnings.warn(
                "Using an Endpoint's exceptions object and an "+\
                "ExceptionRenderer is meaningless. Only the "+\
                "ExceptionRenderer will be used by Nudge when specified.",
                SyntaxWarning
            )

        self.name = name
        self.method = method
        self.uri = uri
        self.function = function
        if args:
            self.sequential, self.named = args
            assert not self.sequential or isinstance(self.sequential, list), \
                "sequential must be a list but was type %s" %\
                type(self.sequential)
            assert not self.named or isinstance(self.named, dict), \
                "named must be a dict, but was type %s" % type(self.named)

        self.exceptions = exceptions
        self.renderer = renderer
        self.regex = re.compile(self.method + self.uri)

    def __call__(self, *args, **kwargs):
        return self.function(*args, **kwargs)

def _write(req, content):
    req._buffer += content

class WSGIRequest(object):

    def __init__(self, req_dict):
        self.req = Dictomatic.wrap(req_dict)
        self.start_time = time.time()
        self.method = self.req['REQUEST_METHOD']
        self.remote_ip = self.req['REMOTE_ADDR']
        self.body = self.req['wsgi.input'].read()
        self._buffer = ''
    
    @lazyprop
    def path(self):
        return self.req['PATH_INFO']

    @lazyprop
    def uri(self):
        return '%s/%s/%s' % (
                self.req['wsgi.url_scheme'], 
                self.req['HTTP_HOST'], 
                self.req['PATH_INFO']
            )

    @lazyprop
    def headers(self):
        _headers = {}
        for k,v in self.req.iteritems():
            if k.startswith('HTTP_'):
                _headers[k.replace('HTTP_', '').lower()] = v
            elif k == 'CONTENT_TYPE':
                _headers['Content-Type'] = v
        return _headers

    @lazyprop
    def arguments(self):
        _arguments = {}
        try:
            tmp = self.req.get('QUERY_STRING', '').split('&')
            tmp = [a.split('=') for a in tmp]
            tmp = filter(lambda x: len(x) == 2, tmp)
            for a in tmp:
                if a[0] in _arguments:
                    _arguments[a[0]].append(a[1])
                else:
                    self.arguments[a[0]] = [a[1]]
        except (Exception), e:
            _log.error(
                'problem making arguments out of QUERY_STRING: %s', 
                self.req['QUERY_STRING']
            )
        return _arguments

    def write(self, content):
        self._buffer += content

    def request_time(self):
        return time.time() - self.start_time

class ServicePublisher(object):

    def __init__(self, fallbackapp=None, endpoints=None, debug=False):
        self._debug = debug
        if self._debug:
            _log.setLevel(logging.DEBUG)
            _root_log.setLevel(logging.DEBUG)
        self._endpoints = []
        if endpoints:
            assert isinstance(endpoints, list), "endpoints must be a list"
            for ep in endpoints:
                self.add_endpoint(ep)
        self._fallbackapp = fallbackapp

    def add_endpoint(self, endpoint):
        assert isinstance(endpoint, Endpoint)
        self._endpoints.append(endpoint)

    def _add_args(self, req):
        args = req.QUERY_STRING.split('=')

    def __call__(self, environ, start_response):
        """ 
            This is called by each request to the server.
            This MUST return a valid HTTP response under all circumstances.
        """
        if isinstance(environ, types.DictType):
            req = WSGIRequest(environ)
        else:
            req = environ

        # main exception handler to ensure client gets valid response.
        # defer any mutation of the request object (incl. writes to the client)
        # until you're sure all exception prone activities have been performed
        # successfully (aka: "basic exception guarantee")
        http_status = None
        final_content = ""
        endpoint = None
        try:
            # allow '_method' query arg to overide method
            method = req.method
            if '_method' in req.arguments:
                method = req.arguments['_method'][0].upper()
                del req.arguments['_method']

            # find appropriate endpoint
            reqline = method + urllib.unquote(req.path)
            match = None
            for endpoint in self._endpoints:
                match = endpoint.regex.match(reqline)
                if match:
                    break

            if not match:
                raise HTTPException(404)
                #
                # Fallback app is untested with WSGI/EVENTLET
                # FIXTHIS!!
                #
                # if self._fallbackapp:
                    # _log.debug("falling through: %s %s" % (method, req.uri))
                    # return self._fallbackapp(event_req, start_response)
                # else:
                    # raise HTTPException(404)

            # convert all values in req.arguments from lists to scalars,
            # then combine with path args.
            arguments = dict((k, v[0]) for k, v in req.arguments.iteritems())
            inargs = dict(match.groupdict(), **arguments)

            
            # add any arguments from JSON body
            if method in ('POST', 'PUT'):
                content_type = req.headers.get("Content-Type", '')
                # add form args
                if content_type.startswith("application/x-www-form-urlencoded"):
                    for name, values in cgi.parse_qs(req.body).iteritems():
                        inargs.setdefault(name, []).extend(values)
                elif content_type.startswith("application/json"):
                    try:
                        body = nudge.json.json_decode(req.body)
                        if isinstance(body, types.DictType):
                            inargs = dict(inargs, **body)

                    except (ValueError):
                        raise HTTPException(400, "body is not JSON")

            # compile positional arguments
            args = []
            for arg in endpoint.sequential:
                args.append(arg.argspec(req, inargs))

            # compile keyword arguments
            kwargs = {}
            for argname, arg in endpoint.named.iteritems():
                r = arg.argspec(req, inargs)
                if r != None:
                    kwargs[argname] = r
                        
            # invoke the service endpoint
            result = endpoint(*args, **kwargs)

            # TODO make sure this works with unicode
            _log.debug(_gen_trace_str(endpoint.function, args, kwargs, result))

            if result == None:
                raise HTTPException(404)
            
            if endpoint.renderer:
                if isinstance(endpoint.renderer, types.TypeType):
                    # support cases where the renderer was specified by the
                    # type and not an instance - todo: Cache renderer
                    endpoint.renderer = endpoint.renderer()
                r = endpoint.renderer(result)
                response, content_type, http_status, extra_headers = \
                    r.content, r.content_type, r.http_status, r.headers
            else:
                # Nudge gives back json by default
                http_status = 200
                content_type = 'application/json; charset=UTF-8'
                response = nudge.json.json_encode(result)
                extra_headers = {}

            final_content = _finish_request(
                req, 
                start_response, 
                http_status, 
                response, 
                content_type, 
                extra_headers
            )

        except (Exception), e:
            if self._debug:
                _log.exception(e)
            else:
                _log.error(e)
            trans = endpoint.renderer
            if trans and isinstance(trans, ExceptionRenderer):
                """ This renderer is supposed to handle exceptions """
                try:
                    r = trans.handle_exception(e)
                except (Exception), e:
                    http_status = 500
                    try:
                        # Sometimes the repr doesn't work so well here
                        _log.error(repr(e.__dict__))
                        msg = e.message
                    except:
                        msg = "Error Handling Exception"
                        _log.exception(msg)
                    final_content = _error_response(
                        req,
                        start_response,
                        http_status,
                        msg,
                    )
                if not final_content:
                    """ Our renderer handled the error correctly """
                    http_status = r.http_status
                    final_content = _finish_request(
                        req,
                        start_response,
                        r.http_status,
                        r.content,
                        r.content_type,
                        r.headers
                    )
            elif isinstance(e, HTTPException):
                http_status = e.status_code
                final_content = _error_response(
                    req, 
                    start_response, 
                    http_status, 
                    e.message
                )
            elif isinstance(e, AssertionError):
                http_status = 400
                final_content = _error_response(
                    req, 
                    start_response, 
                    http_status, 
                    e.message
                )
            else:
                http_status = 500
                if endpoint.exceptions and e.__class__ in endpoint.exceptions:
                    # Our endpoint specified this exception
                    http_status = endpoint.exceptions[e.__class__]
                    try:
                        final_content = _error_response(
                            req, 
                            start_response, 
                            http_status, 
                            e.message, 
                            **e.__dict__
                        )
                    except (Exception), e:
                        _log.exception('Error Handling Exception')
                        final_content = _error_response(
                            req, 
                            start_response, 
                            500, 
                            'Error Handling Exception'
                        )
                else:
                    final_content = _error_response(
                        req, 
                        start_response, 
                        500, 
                        'Unhandled Exception',
                        exception_class=str(e.__class__)
                    )
                    _log.exception('Unhandled Exception')
        _log_access(req, http_status)
        return [final_content + "\r\n"]

def _finish_request(req, start_response, http_status, 
                    response, content_type, extra_headers):

    # Our response must be a byte string
    if isinstance(response, unicode):
        response = response.encode("utf-8", 'replace')

    assert isinstance(response, str), "Response was not a byte string"

    headers = []
    headers.append(('Content-Type', content_type))
    for k, v in extra_headers.items():
        headers.append((k,v))

    start_response(
        str(http_status) + ' ' + responses[http_status], 
        headers
    )
    return response

def _gen_trace_str(f, args, kwargs, res):
    argsstr = ''.join(map(lambda v: "%s, " % v, args))
    kwargsstr = str(kwargs)[1:-1] # remove leading '{' and trailing '}'
    if isinstance(res, unicode):
        return u"%s(%s%s): %s" % (f.__name__, argsstr, kwargsstr, res)
    else:
        return "%s(%s%s): %s" % (f.__name__, argsstr, kwargsstr, res)

def _log_access(req, status_code):
    request_time = 1000.0 * req.request_time()
    _root_log.info("%d %s %s (%s) %.2fms", status_code, req.method, req.uri,
        req.remote_ip, request_time)

def _error_response(req, start_response, status_code, msg, **kwargs):
    """
        Unlike the tornado version, this error response starts the actual
        response back to the client.
    """
    resp_dict = dict(kwargs)
    resp_dict['code'] = status_code
    resp_dict['message'] = msg

    body = nudge.json.json_encode(resp_dict)

    _log.error(
        'Service Publisher error response: %s, %s', 
        status_code,
        req.uri
    )

    headers = []
    headers.append(('Content-Type', 'application/json; charset=UTF-8'))

    start_response(
        str(status_code) + ' ' + responses[status_code], 
        headers
    )
    return body

class HTTPException(Exception):

    def __init__(self, status_code, message=None):
        self.status_code = status_code
        self.message = message

def _generate_headers(version, status_code, content_length, headers={}):
    """generates status line + headers"""
    lines = [version + " " + str(status_code) + " " +
                responses[status_code]]

    lines.extend(["%s: %s" % ('Content-Length', content_length)])
    lines.extend(["%s: %s" % (n, v) for n, v in headers.iteritems()])

    return "\r\n".join(lines) + "\r\n\r\n"


def serve(service_description, args=None):
    if not args:
        args = sys.argv

    #
    # TODO:
    # use arg parse
    # See if we can force the types
    # Print warnings for meaningless options
    # Print a nudge message before starting server
    #
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option(
        "-p", "--port", dest="port", help="port to run on", default=8080)
    parser.add_option(
        "-s", "--server", dest="server", 
        help="which http server to use", default="eventlet")
    # parser.add_option(
        # "-t", "--threaded", dest="threaded", 
        # help="run as a threaded server (paste)", default=False)
    parser.add_option(
        "-n", "--threads", dest="threads", 
        help="number of worker threads (only honored if --threaded)", 
        default=15)
    parser.add_option(
        "-b", "--backlog", dest="backlog", 
        help="maximum number of queued connections (only used if --threaded)", 
        default=5)
    parser.add_option(
        "-d", "--debug", action="store_true", dest="debug", 
        help="setup nudge in debug mode (extra color logging)", default=False)

    (options, args) = parser.parse_args(args)

    if options.debug:
        import nudge.log

    sp = ServicePublisher(
        endpoints=service_description,
        debug=options.debug
    )

    port = int(options.port)
    if str(options.server).strip().lower() == 'paste':
        print "Running paste (multithreaded) on %d" % (port)
        import paste.httpserver
        threads = int(options.threads)
        backlog = int(options.backlog)
        paste.httpserver.serve(
            sp, host=None, port=port, use_threadpool=True, 
            threadpool_workers=threads, threadpool_options=None,
            request_queue_size=backlog
        )
    elif str(options.server).strip().lower() == 'gae':
        from google.appengine.ext.webapp.util import run_wsgi_app
        run_wsgi_app(sp)
    elif str(options.server).strip().lower() == 'tornado':
        pass
    else:
        print "starting eventlet server on port %i" % port
        import eventlet.wsgi
        eventlet.wsgi.server(
            eventlet.listen(('', port)),
            sp,
            max_size=100,
        )

