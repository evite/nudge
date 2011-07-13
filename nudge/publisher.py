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
import cStringIO as StringIO

import nudge.json
import nudge.log
import nudge.arg as args
from nudge.renderer import Json, RequestAwareRenderer
from nudge.validator import ValidationError
from nudge.json import Dictomatic
from nudge.error import handle_exception, HTTPException, JsonErrorHandler,\
    DEFAULT_ERROR_CODE, DEFAULT_ERROR_CONTENT_TYPE, DEFAULT_ERROR_CONTENT, responses

_log = logging.getLogger("nudge.publisher")

__all__ = [
    'Args',
    'Endpoint',
    'WSGIRequest',
    'ServicePublisher',
]

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

    def __init__(self, name=None, method=None, uri=None, uris=None, 
                 function=None, args=None, exceptions=None, renderer=None):
        # Someday support unicode here, for now only bytestrings.
        assert isinstance(name, str)
        assert isinstance(method, str)
        assert (not uris and isinstance(uri, str)) or \
            (not uri and isinstance(uris, types.ListType)), \
            "Endpoints must have either a uri or uris, but not both"
        assert callable(function) or isinstance(function, str), \
            "function must be callable or a string, but was %s" % type(function)

        assert not exceptions or isinstance(exceptions, dict), \
            "exceptions must be a dict, but was type %s" % type(exceptions)
        # TODO maybe do some more checking on exceptions

        self.name = name
        self.method = method
        self.uris = [uri] if uri else uris
        self.function = function
        if args:
            self.sequential, self.named = args
            assert not self.sequential or isinstance(self.sequential, list), \
                "sequential must be a list but was type %s" %\
                type(self.sequential)
            assert not self.named or isinstance(self.named, dict), \
                "named must be a dict, but was type %s" % type(self.named)

        self.exceptions = exceptions
        if renderer:
            if isinstance(renderer, types.TypeType):
                # support cases where the renderer was specified by the
                # type and not an instance - todo: Cache renderer
                self.renderer = renderer()
                warnings.warn(
                    "Endpoint %s was passed an uninstantiated renderer" %\
                    (name))
            else:
                self.renderer = renderer
        else:
            # Nudge default renderer
            self.renderer = Json()
        self.regexs = [re.compile(self.method + uri) for uri in self.uris]

    def match(self, reqline):
        for regex in self.regexs:
            match = regex.match(reqline)
            if match:
                return match


    def __call__(self, *args, **kwargs):
        return self.function(*args, **kwargs)

def _write(req, content):
    req._buffer += content


class WSGIHeaders(dict):

    def __init__(self, *args, **kwargs):
        super(WSGIHeaders, self).__init__()
        self.update(*args, **kwargs)

    def __getitem__(self, key):
        return super(WSGIHeaders, self).__getitem__(
            WSGIHeaders.normalize_name(key)
        )

    def __setitem__(self, key, value):
        return super(WSGIHeaders, self).__setitem__(
            WSGIHeaders.normalize_name(key), value
        )

    def get(self, key, default=None):
        return super(WSGIHeaders, self).get(
            WSGIHeaders.normalize_name(key), default
        )

    def set(self, key, value):
        return super(WSGIHeaders, self).set(
            WSGIHeaders.normalize_name(key), value
        )

    @staticmethod
    def normalize_name(n):
        return n.lower().replace('-','_')


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
        _headers = WSGIHeaders()
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
            # First url decode
            tmp = self.req.get('QUERY_STRING', '')
            if tmp:
                # First url unescape and make unicode. Consider making the
                # unicode decoding type a Nudge option.
                tmp = unicode(urllib.unquote_plus(tmp), encoding="utf-8")
                tmp = tmp.split('&')
                tmp = [a.split('=') for a in tmp]
                # Only keep args with k and v. f= will stay and be [u'f', u'']
                tmp = filter(lambda x: len(x) == 2, tmp)
                for a in tmp:
                    if a[0] in _arguments:
                        _arguments[a[0]].append(a[1])
                    else:
                        _arguments[a[0]] = [a[1]]
        except (Exception), e:
            _log.exception(
                "problem making arguments out of QUERY_STRING: %s",
                self.req['QUERY_STRING']
            )

        if self.method in ('POST', 'PUT') and self.body:
            content_type = self.headers.get("Content-Type", '')
            # TODO make sure these come out as unicode
            if content_type.startswith("application/x-www-form-urlencoded"):
                for name, values in cgi.parse_qs(self.body).iteritems():
                    _arguments.setdefault(name, []).extend(values)
            # multipart form
            elif content_type.startswith("multipart/form-data"):
                try:
                    fs = cgi.FieldStorage(
                        fp=StringIO.StringIO(self.body),
                        environ=self.req,
                        keep_blank_values=1
                    )
                    for k in fs.keys():
                        _arguments[k] = fs[k].value
                except:
                    _log.exception(
                        "problem parsing multipart/form-data"
                    )
            # add any arguments from JSON body
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
                match = endpoint.match(reqline)
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
            arguments = dict((k, v[0]) for k, v in req.arguments.iteritems()\
                if isinstance(v, list) and len(v) > 0)
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

            if isinstance(endpoint.renderer, RequestAwareRenderer):
                r = endpoint.transformer(req, result)
            else:
                r = endpoint.renderer(result)
            content, content_type, code, extra_headers = \
                r.content, r.content_type, r.http_status, r.headers

        except (Exception), e:
            error_response = None
            logged_trace = False
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
                    _log.exception(
                        "Endpoint %s failed to handle exception" % endpoint.name
                    )
                    logged_trace = True

            if not error_response:
                try:
                    # Try one more time to handle a base exception
                    error_response = self._options.default_error_handler(e)
                except (Exception), e:
                    _log.error(
                        "Default error handler failed to handle exception")
                    if logged_trace is False:
                        _log.exception(e)

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

