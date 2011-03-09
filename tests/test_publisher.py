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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import datetime
import time
import unittest
import urlparse
import StringIO

import nudge.validator 

import nudge.arg as args
import nudge.json as json
import nudge.publisher as sp

import httplib
from nudge.publisher import ServicePublisher, Endpoint, Args, WSGIRequest
from nudge.renderer import Result

from nose.tools import raises


class MockResponse(object):
    def __init__(self, request, code, headers={}, buffer=None, effective_url='http://test.example.com', error=None, request_time=None, time_info={}):
        self.request = request
        self.code = code
        self.headers = headers
        self.buffer = buffer
        self._body = None
        self.effective_url = 'http://test.example.com'
        self.request_time = request_time
        self.time_info = time_info

    def _get_body(self):
        return 'test stuff'

    body = property(_get_body)

    def rethrow(self):
        if self.error:
            raise self.error

    def start_response(self, status, headers):
        self.status = status
        self.headers=dict(headers)

    def write(self, content):
        content = ''.join(content)
        lines = ["HTTP/1.1 " + self.status]
        lines.extend(["%s: %s" % ('Content-Length', len(content))])
        lines.extend(["%s: %s" % (n, v) for n, v in self.headers.iteritems()])

        result = "\r\n".join(lines) + "\r\n\r\n" + content
        print 'self request MockResponse', self.request
        self.request.write(result)

    def __repr__(self):
        args = ",".join("%s=%r" % i for i in self.__dict__.iteritems())
        return "%s(%s)" % (self.__class__.__name__, args)


def create_req(method, uri, version='HTTP/1.1', arguments={}, remote_ip='127.0.0.1', headers={}, body=''):
    env = {
        "REQUEST_METHOD": method.upper(),
        "CONTENT_TYPE": "application/json",
        "PATH_INFO": uri,
        "HTTP_HOST": "localhost",
        "REMOTE_ADDR": remote_ip,
        "wsgi.url_scheme": "http",
        "arguments": args,
    }
    env['wsgi.input'] = StringIO.StringIO(body)
    return WSGIRequest(env)


def response_buf(http_status, content, content_type='application/json; charset=UTF-8', headers={}, end='\r\n'):
    lines = ["HTTP/1.1 " + str(http_status) + " " + httplib.responses[http_status]]

    content = content + end
    lines.extend(["%s: %s" % ('Content-Length', len(content))])
    if 'Content-Type' not in headers:
        lines.extend(["%s: %s" % ('Content-Type', content_type)])
    lines.extend(["%s: %s" % (n, v) for n, v in headers.iteritems()])

    return "\r\n".join(lines) + "\r\n\r\n" + content

class StupidTest(unittest.TestCase):

    def test_write(self):
        req = json.Dictomatic({"_buffer":""})
        sp._write(req, "test")
        self.assertEqual(req._buffer, "test")

    def test_args(self):
        self.assertEqual(([], {}), sp.Args())
        now = datetime.datetime.now()
        self.assertEqual(([], {"that":2,"theother":now}), sp.Args(that=2, theother=now))
        self.assertEqual(([1,"this"], {"that":2,"theother":now}), sp.Args(1, "this", that=2, theother=now))

    def test_generate_headers(self):
        result = sp._generate_headers('1', 200, 12, headers={"foo":"bar"})
        self.assertEqual("1 200 OK\r\nContent-Length: 12\r\nfoo: bar\r\n\r\n", result)

    def test_gen_trace_str(self):
        def do_it(): return True
        result = sp._gen_trace_str(do_it, [], {}, "woot")
        self.assertEqual("do_it(): woot", result)
        result = sp._gen_trace_str(do_it, [], {}, u"woot")
        self.assertEqual(u"do_it(): woot", result)

        result = sp._gen_trace_str(do_it, ["yay","boo"], {"fa":"so"}, "woot")
        self.assertEqual("do_it(yay, boo, 'fa': 'so'): woot", result)


class WSGIRequestTest(unittest.TestCase):

    def test_request_fail(self):
        class FooBar():
            def read(self):
                return "woot"
        req_dict = json.Dictomatic.wrap({"QUERY_STRING":datetime.datetime.now(),"REQUEST_METHOD":"POST","HTTP_HOST":"127.0.0.1","PATH_INFO":"test","REMOTE_ADDR":"127.0.0.1","wsgi.input":FooBar(),"wsgi.url_scheme":"toast","headers":{"X-Forwarded-For":"127.0.0.1,something"}, "arguments":{},"body":'{"test":1}'})
        req = sp.WSGIRequest(req_dict)

    def test_request(self):
        class FooBar():
            def read(self):
                return "woot"
        req_dict = json.Dictomatic.wrap({"QUERY_STRING":"blah=woot&test=fa&test=blah","REQUEST_METHOD":"POST","HTTP_HOST":"127.0.0.1","PATH_INFO":"test","REMOTE_ADDR":"127.0.0.1","wsgi.input":FooBar(),"wsgi.url_scheme":"toast","headers":{"X-Forwarded-For":"127.0.0.1,something"}, "arguments":{},"body":'{"test":1}'})
        req = sp.WSGIRequest(req_dict)
        self.assertEquals({"blah":["woot"],"test":["fa","blah"]}, req.arguments)
        self.assertTrue((time.time() - req.start_time < req.request_time()))

class HandlerTest(unittest.TestCase):

    def test_noargs_handlersuccess(self):
        def handler(): return dict(called=1)

        sp = ServicePublisher()
        sp.add_endpoint(Endpoint(name='', method='GET', uri='/location', function=handler))
        req = create_req('GET', '/location')
        resp = MockResponse(req, 200)
        result = sp(req, resp.start_response)
        resp.write(result)
        self.assertEqual(req._buffer,response_buf(200, '{"called": 1}'))
        
    def test_noargs_handlersuccess_empty(self):
        def handler(): return None

        sp = ServicePublisher()
        sp.add_endpoint(Endpoint(name='', method='GET', uri='/location', function=handler))
        req = create_req('GET', '/location')
        resp = MockResponse(req, 200)
        result = sp(req, resp.start_response)
        resp.write(result)
        self.assertEqual(req._buffer,response_buf(404, '{"message": null, "code": 404}'))


    def test_noargs_handlerfail(self):
        def handler(): raise Exception("")

        sp = ServicePublisher()
        sp.add_endpoint(Endpoint(name='', method='GET', uri='/location', function=handler))
        req = create_req('GET', '/location')
        resp = MockResponse(req, 200)
        result = sp(req, resp.start_response)
        resp.write(result)
        self.assertEqual(req._buffer,response_buf(500, '{"exception_class": "<type \'exceptions.Exception\'>", "message": "Unhandled Exception", "code": 500}'))


    def test_matchfailure(self):
        def handler(): pass

        sp = ServicePublisher()
        sp.add_endpoint(Endpoint(name='', method='GET', uri='/location', function=handler))
        req = create_req('GET', '/blah')
        resp = MockResponse(req, 200)
        result = sp(req, resp.start_response)
        resp.write(result)
        self.assertEqual(req._buffer,response_buf(404, '{"message": null, "code": 404}'))

    def test_noargs_but_method_handlersuccess(self):
        def handler(): return dict(arg1=1)

        sp = ServicePublisher()
        sp.add_endpoint(Endpoint(name='', method='DELETE', uri='/location', function=handler))
        req = create_req('DELETE', '/location', arguments=dict(_method=['delete']))
        resp = MockResponse(req, 200)
        result = sp(req, resp.start_response)
        resp.write(result)
        self.assertEqual(req._buffer,response_buf(200, '{"arg1": 1}'))


    def test_arg_handlersuccess(self):
        def handler(*args, **kwargs): return dict(arg1=1)
        sp = ServicePublisher()
        sp.add_endpoint(Endpoint(name='', method='POST', uri='/location', args=([args.String('test')],{}), function=handler))
        req = create_req('POST', '/location', arguments=dict(test="blah"), headers={"Content-Type":"application/json"}, body='{"test":"foo"}')
        resp = MockResponse(req, 200)
        result = sp(req, resp.start_response)
        resp.write(result)
        self.assertEqual(req._buffer,response_buf(200, '{"arg1": 1}'))
        

    def test_arg_handlersuccess_part_deux(self):
        def handler(*args, **kwargs): return dict(arg1=1)
        sp = ServicePublisher()
        sp.add_endpoint(Endpoint(name='', method='POST', uri='/location', args=([],{"test1":args.String('test', optional=True)}), function=handler))
        req = create_req('POST', '/location', arguments=dict(test="blah"), headers={"Content-Type":"application/json"}, body='{"test1":"foo"}')
        resp = MockResponse(req, 200)
        result = sp(req, resp.start_response)
        resp.write(result)
        self.assertEqual(req._buffer,response_buf(200, '{"arg1": 1}'))
        

    def test_arg_handlersuccess_part_tre(self):
        def handler(*args, **kwargs): return dict(arg1=1)
        sp = ServicePublisher()
        sp.add_endpoint(Endpoint(name='', method='POST', uri='/location', args=([args.String('test')],{}), function=handler))
        req = create_req('POST', '/location', arguments=dict(test="blah"), headers={"Content-Type":"application/json"}, body='{"test"="foo"}')
        resp = MockResponse(req, 500)
        result = sp(req, resp.start_response)
        resp.write(result)
        self.assertEqual(req._buffer,response_buf(400, '{"message": "body is not JSON", "code": 400}'))


class RendererTest(unittest.TestCase):
    def test_renderer(self):
        def handler(): return "new_location"
        def renderer(result):
            return Result(
                content='moved',
                content_type='text/html',
                headers={'Location': result },
                http_status=302,
            )

        sp = ServicePublisher()
        sp.add_endpoint(Endpoint(name='', method='GET', uri='/location', function=handler, renderer=renderer))
        req = create_req('GET', '/location')
        resp = MockResponse(req, 200)
        result = sp(req, resp.start_response)
        resp.write(result)
        self.assertEqual(req._buffer,
            response_buf(302, 'moved', content_type='text/html', headers={'Location': 'new_location' })
        )
    
    def test_renderer_fail(self):
        def handler(): return "new_location"
        def renderer(result):
            return Result(
                content='moved',
                content_type='text/html',
                headers={'Location': result },
                http_status=302,
            )

        sp = ServicePublisher()
        sp.add_endpoint(Endpoint(name='', method='GET', uri='/location', function=handler, renderer=renderer))
        req = create_req('GET', '/location')
        resp = MockResponse(req, 200)
        result = sp(req, resp.start_response)
        resp.write(result)
        self.assertEqual(req._buffer,
            response_buf(302, 'moved', content_type='text/html', headers={'Location': 'new_location' })
        )
    
if __name__ == '__main__':
    unittest.main()
