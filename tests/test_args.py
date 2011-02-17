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

import copy
import datetime
import unittest
import StringIO

from nose.tools import raises

from test_publisher import MockResponse, MockRequest

import nudge.arg as args
import nudge.json as json
import nudge.publisher as servicepublisher
from nudge.publisher import WSGIRequest
import nudge.validator as vals

class ValidatorTest(unittest.TestCase):

    def test_string(self):
        inputs = [u'weeweeeeeee', "woot"]
        s = vals.String()
        for input in inputs:
            self.assertEqual(input, s(input))

    @raises(vals.ValidationError)
    def test_string_fail(self):
        inputs = [2, datetime.datetime.now()]
        s = vals.String()
        for input in inputs:
            self.assertEqual(input, s(input))

    def test_datetime(self):
        input = '20100930T112233'
        dt = vals.DateTime()
        self.assertEqual(input, dt(input))

    @raises(vals.ValidationError)
    def test_datetime_failure(self):
        input = '20100930T11T22))33'
        dt = vals.DateTime()
        dt(input)

    def test_date(self):
        input = '20100930'
        d = vals.Date()
        self.assertEqual(datetime.date(2010,9,30), d(input))

    @raises(vals.ValidationError)
    def test_date_failure(self):
        inputs = ['201T0930', '12345', 12345]
        dt = vals.Date()
        for input in inputs:
            dt(input)

    def test_json(self):
        input = '{"test":"Json"}'
        j = vals.Json()
        self.assertEqual({"test":"Json"}, j(input))

    @raises(vals.ValidationError)
    def test_json_fail(self):
        inputs = ['{"test"="Json"}', 1]
        j = vals.Json()
        for input in inputs:
            j(input)

    def test_not_empty(self):
        inputs = ['YAY', 2, datetime.datetime.now()]
        ne = vals.NotEmpty()
        for input in inputs:
            ne(input)

    @raises(vals.ValidationError)
    def test_not_empty_fail(self):
        inputs = [[], '', None, {}]
        ne = vals.NotEmpty()
        for input in inputs:
            ne(input)

    def test_int(self):
        inputs = [1, 30, 30.09, '20']
        i = vals.Int()
        for input in inputs:
            i(input)

    def test_int_min(self):
        inputs = [1, 30, 30.09]
        i = vals.Int(min_=1)
        for input in inputs:
            i(input)

    def test_int_max(self):
        inputs = [1, 30, 30.09]
        i = vals.Int(max_=30)
        for input in inputs:
            i(input)

    def test_int_min_max(self):
        inputs = [2, 30, 30.09]
        i = vals.Int(min_=1, max_=30)
        for input in inputs:
            i(input)

    @raises(vals.ValidationError)
    def test_int_fail(self):
        inputs = ["1.a", datetime.datetime.now()]
        i = vals.Int()
        for input in inputs:
            i(input)

    @raises(vals.ValidationError)
    def test_int_min_fail(self):
        inputs = [1, 30, 30.09]
        i = vals.Int(min_=40)
        for input in inputs:
            i(input)

    @raises(vals.ValidationError)
    def test_int_max_fail(self):
        inputs = [15, 30.09]
        i = vals.Int(max_=10)
        for input in inputs:
            i(input)

    @raises(vals.ValidationError)
    def test_int_min_max_fail(self):
        inputs = [2, 10, 33, 45.09]
        i = vals.Int(min_=20, max_=30)
        for input in inputs:
            i(input)


    def test_float(self):
        inputs = [1, 30, 30.09, "30.45"]
        f = vals.Float()
        for input in inputs:
            f(input)

    def test_float_min(self):
        inputs = [1, 30, 30.09]
        i = vals.Float(min_=1)
        for input in inputs:
            i(input)

    def test_float_max(self):
        inputs = [1, 30, 10, 15]
        i = vals.Float(max_=30)
        for input in inputs:
            i(input)

    def test_float_min_max(self):
        inputs = [2, 10, 29]
        i = vals.Float(min_=1, max_=30)
        for input in inputs:
            i(input)

    @raises(vals.ValidationError)
    def test_float_fail(self):
        inputs = [{"blah":"foo"}, None, "1.a", datetime.datetime.now()]
        f = vals.Float()
        for input in inputs:
            f(input)

    @raises(vals.ValidationError, TypeError)
    def test_float_min_type_fail(self):
        inputs = [1, 30, 30.09]
        i = vals.Float(min_=datetime.datetime.now())

    @raises(vals.ValidationError)
    def test_float_min_fail(self):
        inputs = [1, 30, 30.09]
        i = vals.Float(min_=40)
        for input in inputs:
            i(input)

    @raises(vals.ValidationError)
    def test_float_max_fail(self):
        inputs = [15, 30.09]
        i = vals.Float(max_=10)
        for input in inputs:
            i(input)

    @raises(vals.ValidationError, TypeError)
    def test_float_max_type_fail(self):
        inputs = [15, 30.09]
        i = vals.Float(max_=datetime.datetime.now())

    @raises(vals.ValidationError, TypeError)
    def test_float_min_max_fail(self):
        inputs = [2, 10, 33, 45.09]
        i = vals.Float(min_=datetime.datetime.now(), max_=datetime.datetime.now())

    def test_string_alts(self):
        inputs = ['yay', 'boo', 'foo', 'jeebus']
        alts = ['yay', 'yay', 'boo', 'foo', 'jeebus']
        a = vals.StringAlternatives(alts)
        for input in inputs:
            a(input)

    @raises(vals.ValidationError)
    def test_string_alts_fail(self):
        inputs = [1, datetime.datetime.now(), 'woot']
        alts = ['yay', 'yay', 'boo', 'foo', 'jeebus']
        a = vals.StringAlternatives(alts)
        for input in inputs:
            a(input)

    def test_boolean(self):
        inputs = [False, True, 0, 1, 'true', 'false']
        b = vals.Boolean()
        for input in inputs:
            b(input)

    @raises(vals.ValidationError)
    def test_boolean_fail(self):
        inputs = [{}, [], 20, datetime.datetime.now()]
        b = vals.Boolean()
        for input in inputs:
            b(input)


_base_environ = {
    "REQUEST_METHOD": "GET",
    "CONTENT_TYPE": "application/json",
    "PATH_INFO": "/",
    "HTTP_HOST": "localhost",
    "REMOTE_ADDR": "127.0.0.1",
    "wsgi.url_scheme": "http",
}
def create_req(environ):
    new_env = copy.copy(_base_environ)
    new_env.update(environ)
    new_env['wsgi.input'] = StringIO.StringIO(new_env.get('body', ''))
    return WSGIRequest(new_env)

class ArgTest(unittest.TestCase):
    
    def test_get_json_body(self):
        req = create_req({"body":'{"woot":"bar"}', "REQUEST_METHOD":"POST"})
        body = args._get_json_body(req)
        self.assertEqual({"woot":"bar"}, body)

    def test_get_json_body_cached(self):
        req = create_req({"body":'{"yay":12345}'})
        self.assertEqual({"yay":12345}, args._get_json_body(req))
        # remove the body
        req.body = ''
        self.assertEqual({"yay":12345}, args._get_json_body(req))

    def test_get_no_json_body(self):
        req = create_req({"arguments":{}})
        body = args._get_json_body(req)
        self.assertEqual(None, body)

    @raises(servicepublisher.HTTPException)
    def test_get_bad_json_body(self):
        req = create_req({"arguments":{},"body":'{"woot"="bar"}'})
        body = args._get_json_body(req)

    def test_empty_json_body(self):
        req = create_req({"arguments":{}})
        jb = args.JsonBody(optional=True)
        self.assertEqual(None, jb.argspec(req, None))

    @raises(servicepublisher.HTTPException)
    def test_empty_json_body_fail(self):
        req = create_req({"arguments":{}})
        jb = args.JsonBody()
        jb.argspec(req, None)

    def test_json_body(self):
        req = create_req({"arguments":{},"body":'{"test":"bar"}'})
        jb = args.JsonBody()
        self.assertEqual({"test":"bar"}, jb.argspec(req, None))

    def test_extend_json_body(self):
        req = create_req({"body":'{"test":"bar"}', "REQUEST_METHOD":"POST"})
        print req.headers
        jb = args.JsonBody(extend={"foo":"blah"})
        self.assertEqual({"test":"bar", "foo":"blah"}, jb.argspec(req, None))

    def test_json_body_field(self):
        req = create_req({"arguments":{},"body":'{"test":"bar"}'})
        jbf = args.JsonBodyField("test")
        self.assertEqual("bar", jbf.argspec(req, None))

    @raises(servicepublisher.HTTPException)
    def test_json_body_field_fail(self):
        req = create_req({"arguments":{},"body":'{"test":"bar"}'})
        jbf = args.JsonBodyField("foo")
        jbf.argspec(req, None)

    def test_json_body_field_optional(self):
        req = create_req({"arguments":{},"body":'{"test":"bar"}'})
        jbf = args.JsonBodyField("foo", optional=True)
        self.assertEqual(None, jbf.argspec(req, None))

    @raises(servicepublisher.HTTPException)
    def test_json_body_field_optional_fail(self):
        req = create_req({"arguments":{},"body":'{"test":"bar"}'})
        jbf = args.JsonBodyField("foo", optional=False)
        jbf.argspec(req, None)

    def test_client_ip(self):
        req = create_req({"headers":{"X-Forwarded-For":"127.0.0.1,something"}, "arguments":{},"body":'{"test":1}'})
        ip = args.ClientIp()
        self.assertEqual("127.0.0.1", ip.argspec(req, None))

        req2 = create_req({"headers":{},"remote_ip":"127.0.0.1", "arguments":{},"body":'{"test":1}'})
        self.assertEqual("127.0.0.1", ip.argspec(req2, None))

    def test_request_header(self):
        dicta = json.Dictomatic.wrap({"headers":{"test":"something"}, "arguments":{},"body":'{"test":1}'})
        rh = args.RequestHeader("test")
        self.assertEqual("something", rh.argspec(dicta, None))
        dictb = json.Dictomatic.wrap({"headers":{"test":"anotherthing"}, "arguments":{},"body":'{"test":1}'})
        self.assertEqual("anotherthing", rh.argspec(dictb, None))
        dictb = json.Dictomatic.wrap({"headers":{"toast":"anotherthing"}, "arguments":{},"body":'{"test":1}'})
        self.assertEqual(None, rh.argspec(dictb, None))

    def test_string_in_body(self):
        req = create_req({"headers":{"test":"something"}, "arguments":{},"body":'{"test":1}'})
        i = args.String("test")
        self.assertEqual(1, i.argspec(req, None))

    def test_string_in_args(self):
        req = create_req({"QUERY_STRING":"test=1"})
        i = args.String("test")
        self.assertEqual("1", i.argspec(req, None))

    def test_string_in_inargs(self):
        req = create_req({"headers":{"test":"something"}, "arguments":{},"body":'{}'})
        i = args.String("test")
        self.assertEqual(1, i.argspec(req, {"test":1}))

    @raises(servicepublisher.HTTPException)
    def test_string_in_inargs_but_none(self):
        req = create_req({"headers":{"test":"something"}, "arguments":{},"body":'{}'})
        i = args.String("test")
        self.assertEqual(1, i.argspec(req, {"test":None}))

    @raises(servicepublisher.HTTPException)
    def test_string_optional_false(self):
        req = create_req({"headers":{"test":"something"}, "arguments":{},"body":'{"test":1}'})
        i = args.String("test1", optional=False)
        i.argspec(req, None)

    def test_string_optional_true(self):
        req = create_req({"headers":{"test":"something"}, "arguments":{},"body":'{"test":1}'})
        i = args.String("test1", optional=True)
        self.assertEqual(None, i.argspec(req, None))

    def test_arg_optional_true_with_default(self):
        req = create_req({"headers":{"test":"something"}, "arguments":{},"body":'{"test":1}'})
        def validator(s, y): return s.get('blah')
        i = args.Arg("test1", optional=True, default=12345, validator=validator)
        self.assertEqual(12345, i.argspec(req, None))

    # def test_file(self):
        # req = create_req({"headers":{"test":"something"}, "files":{"test":[{"filename":"toast", "body":"blah", "content_type":"foobar"}]}, "arguments":{},"body":'{"test":1}'})
        # i = args.UploadedFile("test")
        # self.assertEqual({"filename":"toast", "data":"blah", "content_type":"foobar"}, i.argspec(req, None))

    def test_integer(self):
        req = create_req({"headers":{"test":"something"}, "arguments":{},"body":'{"test":1}'})
        i = args.Integer("test")
        self.assertEqual(1, i.argspec(req, None))

    @raises(servicepublisher.HTTPException)
    def test_integer_fail(self):
        req = create_req({"headers":{"test":"something"}, "arguments":{},"body":'{"test":"awe"}'})
        i = args.Integer("test")
        i.argspec(req, None)

    def test_plain_arg(self):
        req = create_req({"headers":{"test":"something"}, "arguments":{},"body":'{"test":1}'})
        def validator(s): return s
        a = args.Arg("test", optional=True, default="foobar", validator=validator)
        self.assertEqual(1, a.argspec(req, None))
        self.assertNotEqual(None, a.argspec(req, None))

    @raises(AttributeError)
    def test_plain_arg_fail(self):
        a = args.Arg("test", optional=True, default="foobar")
        a.argspec({},None)

    # def test_plain_arg_return_none(self):
        # req = create_req({"headers":{"test":"something"}, "arguments":{'woot':'far'},"body":'{"test":1}'})
        # a = args.Arg("test", optional=True)
        # def validator(s, p): return s.get('s') or p.get('s')
        # a.argspec = validator
        # self.assertEqual(None, a.argspec(req,{}))

    @raises(AttributeError)
    def test_no_validators(self):
        req = create_req({"arguments":{}})
        jb = args.Arg("a")
        jb.argspec(req, None)


    def test_custom_arg(self):
        ca = args.CustomArg()
        self.assertEqual(None, ca.argspec())
        def validator(s): return s
        def invalidator(s): return 1
        ca.argspec = validator

        self.assertEqual(validator, ca.argspec)
        self.assertEqual(validator(None), ca.argspec(None))
        self.assertEqual("test", ca.argspec("test"))
        self.assertNotEqual("nottest", ca.argspec("test"))
        self.assertNotEqual(invalidator(None), ca.argspec(None))
        self.assertNotEqual(invalidator, ca.argspec)

