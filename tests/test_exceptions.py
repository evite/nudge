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

import httplib
from nudge.publisher import ServicePublisher, Endpoint, Args, WSGIRequest,\
    HTTPException, responses
from nudge.renderer import Result

from nose.tools import raises

from test_publisher import create_req, MockResponse, response_buf

class ExceptionTest(unittest.TestCase):
    # TODO figure out a way to determine which names are unused aka imports

    #
    # Tests to add:
    #    - Test httpexp with bad code
    #    - Test httpexp with no message
    #    - Test using a custom error handler
    #

    def test_success(self):
        """ Control test. Default content type (json) """

        def handler(): 
            return "basic string"
        
        sp = ServicePublisher()
        sp.add_endpoint(Endpoint(
            name='test', 
            method='GET', 
            uri='/location', 
            function=handler
        ))
        req = create_req('GET', '/location')
        resp = MockResponse(req, 200)
        result = sp(req, resp.start_response)
        resp.write(result)
        self.assertEqual(req._buffer,response_buf(200, '"basic string"'))

    def test_default_exp(self):
        """ Test the base exception handling where we dont have a callable
            function, but we have some defaults to use """

        def handler(): 
            raise Exception("Someone screwed the pooch")
        
        sp = ServicePublisher()
        sp.add_endpoint(Endpoint(
            name='test', 
            method='GET', 
            uri='/location', 
            function=handler,
        ))
        req = create_req('GET', '/location')
        resp = MockResponse(req, 500)
        result = sp(req, resp.start_response)
        resp.write(result)
        self.assertEqual(req._buffer,response_buf(
            500, '{"message": "%s", "code": 500}' % (responses[500])))

    def test_assertion_exp(self):
        """ Test throwing an assertion error which will result in 400 and
            return the actual exception message. """

        def handler(): 
            raise AssertionError("Someone screwed the pooch")
        
        sp = ServicePublisher()
        sp.add_endpoint(Endpoint(
            name='test', 
            method='GET', 
            uri='/location', 
            function=handler,
        ))
        req = create_req('GET', '/location')
        resp = MockResponse(req, 400)
        result = sp(req, resp.start_response)
        resp.write(result)
        self.assertEqual(req._buffer,response_buf(
            400, '{"message": "Someone screwed the pooch", "code": 400}'))

    def test_http_exp_with_msg(self):
        """ Test using HTTPException which will give back an actual
            http code and a custom message """

        def handler(): 
            raise HTTPException(503, "This message is used when provided")
        
        sp = ServicePublisher()
        sp.add_endpoint(Endpoint(
            name='test', 
            method='GET', 
            uri='/location', 
            function=handler,
        ))
        req = create_req('GET', '/location')
        resp = MockResponse(req, 503)
        result = sp(req, resp.start_response)
        resp.write(result)
        self.assertEqual(req._buffer,response_buf(
            503, '{"message": "%s", "code": 503}' % \
            ('This message is used when provided')))

    def test_http_exp_without_msg(self):
        """ Test using HTTPException which will give back an actual
            http code and a default message """

        def handler(): 
            raise HTTPException(503)
        
        sp = ServicePublisher()
        sp.add_endpoint(Endpoint(
            name='test', 
            method='GET', 
            uri='/location', 
            function=handler,
        ))
        req = create_req('GET', '/location')
        resp = MockResponse(req, 503)
        result = sp(req, resp.start_response)
        resp.write(result)
        self.assertEqual(req._buffer,response_buf(
            503, '{"message": "%s", "code": 503}' % \
            (responses[503])))

    def test_default_exp_handler(self):
        """ Test default exception handler without a callable. """
        class TestExpHandler(object):
            code = 500
            content_type = "text/plain"
            content = "An error occured"
            headers = {}

        def handler():
            raise Exception(500)
        
        sp = ServicePublisher(
                options={"default_error_handler": TestExpHandler})
        sp.add_endpoint(Endpoint(
            name='test', 
            method='GET', 
            uri='/location', 
            function=handler,
        ))
        req = create_req('GET', '/location')
        resp = MockResponse(req, 500)
        result = sp(req, resp.start_response)
        resp.write(result)
        self.assertEqual(req._buffer, response_buf(
            http_status=500,
            content="An error occured",
            content_type="text/plain",
        ))

    def test_default_exp_handler_with_call(self):
        """ Test default exception handler with a callable that will change
            message. """
        class TestExpHandler(object):
            code = 500
            content_type = "text/plain"
            content = "An error occured"
            headers = {}
            def __call__(self, exp):
                return (self.code, self.content_type, exp.message, self.headers)

        def handler():
            raise Exception("New Message")
        
        sp = ServicePublisher(
                options={"default_error_handler": TestExpHandler})
        sp.add_endpoint(Endpoint(
            name='test', 
            method='GET', 
            uri='/location', 
            function=handler,
        ))
        req = create_req('GET', '/location')
        resp = MockResponse(req, 500)
        result = sp(req, resp.start_response)
        resp.write(result)
        self.assertEqual(req._buffer, response_buf(
            http_status=500,
            content="New Message",
            content_type="text/plain",
        ))

    def test_custom_exp_handler_precidence(self):
        """ Test a custom exception handler without a callable. Map to our
            endpoint, and do not use a default handler (will default to
            JsonErrorHandler) """
        class TestExpHandler(object):
            code = 500
            content_type = "text/plain"
            content = "Default error message"
            headers = {}

        class SpecificExpHandler(object):
            code = 502
            content_type = "text/plain"
            content = "Specific Error Message"
            headers = {}

        class SpecificException(Exception):
            pass

        class MoreSpecificException(SpecificException):
            pass

        def handler():
            raise MoreSpecificException("New Message")
        
        sp = ServicePublisher()
        sp.add_endpoint(Endpoint(
            name='test', 
            method='GET', 
            uri='/location', 
            function=handler,
            exceptions={
                Exception:TestExpHandler(),
                SpecificException:SpecificExpHandler(),
            }
        ))
        req = create_req('GET', '/location')
        resp = MockResponse(req, 500)
        result = sp(req, resp.start_response)
        resp.write(result)
        self.assertEqual(req._buffer, response_buf(
            http_status=502,
            content="Specific Error Message",
            content_type="text/plain",
        ))

    def test_custom_exp_handler(self):
        """ Test a custom exception handler without a callable. Map to our
            endpoint, and do not use a default handler (will default to
            JsonErrorHandler) """
        class TestExpHandler(object):
            code = 500
            content_type = "text/plain"
            content = "Default error message"
            headers = {}

        def handler():
            raise Exception("New Message")
        
        sp = ServicePublisher()
        sp.add_endpoint(Endpoint(
            name='test', 
            method='GET', 
            uri='/location', 
            function=handler,
            exceptions={Exception:TestExpHandler()}
        ))
        req = create_req('GET', '/location')
        resp = MockResponse(req, 500)
        result = sp(req, resp.start_response)
        resp.write(result)
        self.assertEqual(req._buffer, response_buf(
            http_status=500,
            content="Default error message",
            content_type="text/plain",
        ))

    def test_custom_exp_handler_with_callable(self):
        """ Test a custom exception handler with a callable that will return
            the exception message instead of default. Map to our
            endpoint, and do not use a default handler (will default to
            JsonErrorHandler) """
        class TestExpHandler(object):
            code = 500
            content_type = "text/plain"
            content = "Default error message"
            headers = {}
            def __call__(self, exp):
                return (self.code, self.content_type, exp.message, self.headers)


        def handler():
            raise Exception("New Message")
        
        sp = ServicePublisher()
        sp.add_endpoint(Endpoint(
            name='test', 
            method='GET', 
            uri='/location', 
            function=handler,
            exceptions={Exception:TestExpHandler()}
        ))
        req = create_req('GET', '/location')
        resp = MockResponse(req, 500)
        result = sp(req, resp.start_response)
        resp.write(result)
        self.assertEqual(req._buffer, response_buf(
            http_status=500,
            content="New Message",
            content_type="text/plain",
        ))

    def test_custom_exp_handler_with_callable_fail(self):
        """ Test a custom exception handler with a callable that will raise
            an exception and force SP to use the default exception handling. Map to our
            endpoint, and do not use a default handler (will default to
            JsonErrorHandler) """
        class TestExpHandler(object):
            code = 500
            content_type = "text/plain"
            content = "Default error message"
            headers = {}
            def __call__(self, exp):
                """ Note that doing this now hides the original exception """
                raise Exception("Something really bad happened")

        def handler():
            raise Exception("New Message")
        
        sp = ServicePublisher(debug=True, endpoints=[
            Endpoint(
            name='test', 
            method='GET', 
            uri='/location', 
            function=handler,
            exceptions={Exception:TestExpHandler()}
        )])
        req = create_req('GET', '/location')
        resp = MockResponse(req, 500)
        result = sp(req, resp.start_response)
        resp.write(result)
        self.assertEqual(req._buffer, response_buf(
            http_status=500,
            content='{"message": "%s", "code": 500}' % (responses[500]),
        ))

    def test_custom_default_exp_handler(self):
        class VerboseJsonException(object):
            content_type = "application/json; charset=UTF-8"
            content = "Unknown Error"
            headers = {}
            code = 500

            def __init__(self, code=None):
                if code:
                    self.code = code 

            def __call__(self, exception):
                resp = exception.__dict__
                code = self.code
                if hasattr(exception, 'status_code'):
                    code = exception.status_code
                resp['code'] = code
                if hasattr(exception, 'message'):
                    resp['message'] = exception.message
                if not resp.get('message'):
                    _log.debug("Exception: {0}".format(exception))
                    resp['message'] = str(exception)
                return (
                    code,
                    self.content_type,
                    nudge.json.json_encode(resp),
                    {},
                )

        def handler():
            raise Exception("New Message")
        
        sp = ServicePublisher(debug=True, endpoints=[
            Endpoint(
            name='test', 
            method='GET', 
            uri='/location503', 
            function=handler,
            exceptions={Exception:503}),
            Endpoint(
            name='test', 
            method='GET', 
            uri='/location500', 
            function=handler,
        )],
        default_error_handler=VerboseJsonException)

        req = create_req('GET', '/location503')
        resp = MockResponse(req, 503)
        result = sp(req, resp.start_response)
        resp.write(result)
        self.assertEqual(req._buffer, response_buf(
            http_status=503,
            content='{"message": "New Message", "code": 503}',
        ))

        req = create_req('GET', '/location500')
        resp = MockResponse(req, 500)
        result = sp(req, resp.start_response)
        resp.write(result)
        self.assertEqual(req._buffer, response_buf(
            http_status=500,
            content='{"message": "New Message", "code": 500}',
        ))

if __name__ == '__main__':
    unittest.main()

