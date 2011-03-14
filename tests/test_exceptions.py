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

    def test_custom_exp_handler(self):
        """ Test default exception handler without a callable.
            This will default to """
        class TestExpHandler(object):
            code = 500
            content_type = "text/plain"
            content = "An error occured"
            headers = {}

        def handler():
            raise Exception(503)
        
        sp = ServicePublisher(
                options={"default_error_handler": TestExpHandler()})
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
        self.assertEqual(req._buffer, response_buf(
            http_status=503,
            content="An error occured",
            content_type="text/plain",
        ))

if __name__ == '__main__':
    unittest.main()

