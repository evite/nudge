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

import nudge.json
import nudge.log
import nudge.arg as args
from nudge.validator import ValidationError
from nudge.renderer import ExceptionRenderer
from nudge.json import Dictomatic

_log = logging.getLogger("nudge.servicepublisher")

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

DEFAULT_ERROR_CODE = 500
DEFAULT_ERROR_CONTENT_TYPE = "application/json; charset=UTF-8"
DEFAULT_ERROR_CONTENT = '{"message": "%s", "code": %i}' % (
    responses[DEFAULT_ERROR_CODE],
    DEFAULT_ERROR_CODE,
)
   
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
        # TODO maybe do some more checking on exceptions

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
        return '%s://%s%s' % (
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
                    _arguments[a[0]] = [a[1]]
        except (Exception), e:
            _log.error(
                'problem making arguments out of QUERY_STRING: %s', 
                self.req['QUERY_STRING']
            )

        # add any arguments from JSON body
        if self.method in ('POST', 'PUT') and self.body:
            content_type = self.headers.get("Content-Type", '')
            # add form args
            if content_type.startswith("application/x-www-form-urlencoded"):
                for name, values in cgi.parse_qs(self.body).iteritems():
                    _arguments.setdefault(name, []).extend(values)
            elif content_type.startswith("application/json"):
                try:
                    body = nudge.json.json_decode(self.body)
                    if isinstance(body, types.DictType):
                        _arguments = dict(_arguments, **body)

                except (ValueError):
                    raise HTTPException(400, "body is not JSON")

        return _arguments

    def write(self, content):
        self._buffer += content

    def request_time(self):
        return time.time() - self.start_time

def redirect(uri, headers=None):
    if not headers:
        headers = {}
    headers['Location'] = uri
    return (302,
        'text/html; charset=utf-8',
        """
<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">
<HTML>
<HEAD>
<TITLE>Moved</TITLE>
</HEAD>
<BODY>
<H2>Moved</H2>
<A HREF="%s">The requested URL has moved here.</A>
</BODY>
</HTML>""" % uri,
        headers
    )

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

class ServicePublisher(object):

    def __init__(self, fallbackapp=None, endpoints=None, \
                 debug=False, options=None):
        self._debug = debug
        if self._debug:
            _log.setLevel(logging.DEBUG)
        self._endpoints = []
        if endpoints:
            assert isinstance(endpoints, list), "endpoints must be a list"
            for ep in endpoints:
                self.add_endpoint(ep)
        # TODO Fix fallback app here and below
        self._fallbackapp = fallbackapp

        self._options = Dictomatic({
            "default_error_handler": JsonErrorHandler(),
        })

        if options:
            assert isinstance(options, dict), "options must be of type dict"
            self._options.update(options)
        self.verify_options()
            
    def verify_options(self):
        msg = "Default exception handler "
        assert self._options.default_error_handler, msg + "must exist"
        assert isinstance(self._options.default_error_handler.code, int),\
            msg + "http code must be an int"
        assert self._options.default_error_handler.code in responses,\
            msg + "http code not in nudge.publisher.responses"
        assert isinstance(
            self._options.default_error_handler.content_type, str),\
            msg + "content_type must be a byte string"
        assert isinstance(self._options.default_error_handler.content, str),\
            msg + "content must be a byte string"
        assert isinstance(self._options.default_error_handler.headers, dict),\
            msg + "headers must be a dict"

        for k, v in self._options.default_error_handler.headers:
            assert isinstance(k, str),\
                msg+ "headers keys and values must be a byte string"
            assert isinstance(v, str),\
                msg + "headers keys and values must be a byte string"

        # Set default error params here incase of massive failure we fallback
        # to these.
        self._options.default_error_response = (
            self._options.default_error_handler.code,
            self._options.default_error_handler.content_type,
            self._options.default_error_handler.content,
            self._options.default_error_handler.headers,
        )

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
        code = None
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
                # TODO: Handle HTTPException in new world exceptions
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
            
            if endpoint.renderer:
                if isinstance(endpoint.renderer, types.TypeType):
                    # support cases where the renderer was specified by the
                    # type and not an instance - todo: Cache renderer
                    endpoint.renderer = endpoint.renderer()
                r = endpoint.renderer(result)
                content, content_type, code, extra_headers = \
                    r.content, r.content_type, r.http_status, r.headers
            elif result == None:
                raise HTTPException(404)
            else:
                # Nudge gives back json by default
                code = 200
                content_type = DEFAULT_ERROR_CONTENT_TYPE
                content = nudge.json.json_encode(result)
                extra_headers = {}

        except (Exception), e:
            error_response = None
            #
            # Try to use this endpoint's exception handler(s)
            # If the raised exception is not mapped in this endpoint, or
            # this endpoint raises an exception when trying to handle, 
            # we will then try to the default handler, and ultimately
            # fallback to the self._options.default_error_response, which
            # is guaranteed to be valid at app initialization.
            #
            if endpoint and endpoint.exceptions:
                try:
                    error_response = handle_exception(e, endpoint.exceptions)
                except (Exception), e:
                    # TODO this may log too loudly
                    _log.exception("Endpoint failed to handle exception")

            if not error_response:
                try:
                    # Try one more time to handle a base exception
                    error_response = self._options.default_error_handler(e)
                except (Exception), e:
                    _log.exception(
                        "Default error handler failed to handle exception")

            code, content_type, content, extra_headers = \
                error_response or self._options.default_error_response

        final_content = _finish_request(
            req, 
            start_response, 
            code, 
            content_type, 
            content, 
            extra_headers
        )

        return [final_content + "\r\n"]

def handle_exception(exp, exp_handlers):
    # Check if this endpoint can handle this exception
    if exp_handlers and exp.__class__ in exp_handlers:
        exp_handler = exp_handlers[exp.__class__]
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

def _finish_request(req, start_response, code, content_type, content, headers):
    try:
        if isinstance(content, unicode):
            content = content.encode("utf-8", 'replace')
        assert isinstance(content, str), "Content was not a byte string"
        assert isinstance(content_type, str), \
            "Content Type was not a byte string"
        final_headers = []
        final_headers.append(('Content-Type', content_type))
        if headers:
            for k, v in headers.items():
                assert isinstance(k, str), \
                    "Headers keys and values must be a byte string"
                final_headers.append((k,v))

    except (Exception), e:
        _log.exception(e)
        final_headers = [('Content-Type', DEFAULT_ERROR_CONTENT_TYPE)]
        content = DEFAULT_ERROR_CONTENT
        code = DEFAULT_ERROR_CODE

    start_response(
        str(code) + ' ' + responses[code], 
        final_headers
    )
    return content

def _gen_trace_str(f, args, kwargs, res):
    argsstr = ''.join(map(lambda v: "%s, " % v, args))
    kwargsstr = str(kwargs)[1:-1] # remove leading '{' and trailing '}'
    if isinstance(res, unicode):
        return u"%s(%s%s): %s" % (f.__name__, argsstr, kwargsstr, res)
    else:
        return "%s(%s%s): %s" % (f.__name__, argsstr, kwargsstr, res)

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
        nudge.log.try_color_logging()

    sp = ServicePublisher(
        endpoints=service_description,
        debug=options.debug
    )
    sp = nudge.log.LoggingMiddleware(sp)

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

