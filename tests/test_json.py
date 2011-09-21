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
import unittest

from nose.tools import raises

import nudge.json as json


class JsonTest(unittest.TestCase):

    def test_string_keys(self):
        now = datetime.datetime.now()
        dicta = {1:1,"2":2,"theeeee":now}
        result = json.json_ensure_string_keys(dicta)
        self.assertEqual({"1":1,"2":2,"theeeee":now}, result)

    def test_none(self):
        result = json.Dictomatic.wrap(None)
        self.assertEqual({}, result)

    def test_dictomatic_from_string(self):
        data = '{"test":2,"blah":"woot","things":[12,123,1234]}'
        result = json.Dictomatic.wrap(data)
        self.assertEqual({"test":2,"blah":"woot","things":[12,123,1234]}, result)

    def test_dictomatic_from_string_with_subdict(self):
        data = '{"test":2,"blah":"woot","things":[12,123,1234],"this":{"me":"my"}}'
        result = json.Dictomatic.wrap(data)
        self.assertEqual({"test":2,"blah":"woot","things":[12,123,1234],"this":{"me":"my"}}, result)

    def test_dictomatic_from_string_with_sublistdict(self):
        data = '{"test":2,"blah":"woot","things":[{"yo":"mans"}],"this":{"me":"my"}}'
        result = json.Dictomatic.wrap(data)
        self.assertEqual({"test":2,"blah":"woot","things":[{"yo":"mans"}],"this":{"me":"my"}}, result)

    # We removed this functionality as the caller of Dictomatic should use
    # a list comprehension for this sort of thing.
    @raises(ValueError)
    def test_dictomatic_from_string_list(self):
        data = '[{"test":2,"blah":"woot","things":[12,123,1234]}, {"test":2,"blah":"woot","things":[12,123,1234]}]'
        results = json.Dictomatic.wrap(data)
        for result in results:
            self.assertEqual({"test":2,"blah":"woot","things":[12,123,1234]}, result)

    def test_dictomatic_from_dict(self):
        data = {"test":2,"blah":"woot","things":[12,123,1234]}
        result = json.Dictomatic.wrap(data)
        self.assertEqual({"test":2,"blah":"woot","things":[12,123,1234]}, result)

    def test_dictomatic_from_dictomatic(self):
        data = json.Dictomatic.wrap({"test":2,"blah":"woot","things":[12,123,1234]})
        result = json.Dictomatic.wrap(data)
        self.assertEqual(data, result)

    @raises(ValueError)
    def test_bad_dict(self):
        json.Dictomatic.wrap(datetime.datetime.now())

    def test_encode(self):
        data = '{"test_that":3, "testThis":2,"blah":"woot","things":[12,123,1234],"this":{"me":"my"}}'
        result = json.Dictomatic.wrap(data)
        data2 = json.json_encode(result)
        result2 = json.Dictomatic.wrap(data2)
        self.assertEqual(result, result2)

    def test_encode_date(self):
        data = datetime.datetime.now()
        print "data.ctime", data.ctime()
        print "json_encode data", json.json_encode(data)
        self.assertEqual('"'+data.ctime()+'"', json.json_encode(data))

    def test_encode_normal(self):
        class Foo(json.JsonSerializable):
            __dict__ = {"test":1}
        data = {"test_that":Foo(), "testThis":2,"blah":"woot","things":[12,123,1234],"this":{"me":"my"}}
        data_str = '{"testThis": 2, "test_that": {"test": 1}, "this": {"me": "my"}, "things": [12, 123, 1234], "blah": "woot"}'
        self.assertEqual(data_str, json.json_encode(data))

    def test_encode_custom_class(self):
        class Bar(json.JsonSerializable):
            __dict__ = {"foo":"bar"}
        class Foo(json.JsonSerializable):
            __dict__ = {"blah":Bar()}
        self.assertEqual('{"blah": {"foo": "bar"}}', json.json_encode(Foo()))

    @raises(TypeError)
    def test_encode_fail(self):
        class Foo():
            def __repr__(self):
                return '{"test":1}'
        json.json_encode(Foo())

    def test_gets(self):
        data = '{"test_that":3, "testThis":2,"blah":"woot","things":[12,123,1234],"this":{"me":"my"}}'
        result = json.Dictomatic.wrap(data)
        self.assertEqual(2, result['testThis'])
        self.assertEqual(2, result.testThis)
        self.assertEqual(2, result.test_this)
        self.assertEqual(2, result.get('test_this', 2))

        self.assertEqual(3, result['test_that'])
        self.assertEqual(3, result.testThat)
        self.assertEqual(3, result.test_that)
        self.assertEqual(3, result.get('test_that', 4))

    def test_sets(self):
        data = '{"testThis":2,"blah":"woot","things":[12,123,1234],"this":{"me":"my"}}'
        result = json.Dictomatic.wrap(data)
        result.blahThis = 2
        self.assertEqual(2, result.blahThis)
        self.assertEqual(2, result.blah_this)
        self.assertEqual(2, result['blahThis'])

    @raises(AttributeError)
    def test_bad_get_attr(self):
        data = '{"testThis":2,"blah":"woot","things":[12,123,1234],"this":{"me":"my"}}'
        result = json.Dictomatic.wrap(data)
        result.__bad__

    def test_bad_get_dot_attr(self):
        data = '{"testThis":2,"blah":"woot","things":[12,123,1234],"this":{"me":"my"}}'
        result = json.Dictomatic.wrap(data)
        self.assertEqual(None, result.bad_thing)

    @raises(KeyError)
    def test_bad_get_bad_key(self):
        data = '{"testThis":2,"blah":"woot","things":[12,123,1234],"this":{"me":"my"}}'
        result = json.Dictomatic.wrap(data)
        self.assertEqual(None, result['bad_thing'])

