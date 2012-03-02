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

import datetime
import re
import types
import json
testsdf = '''
try:
    from simplejson import JSONEncoder, JSONDecoder
except ImportError:
    try:
        # See if appengine has this module
        from django.utils.simplejson import JSONEncoder, JSONDecoder
    except ImportError:
        try:
            from json import JSONEncoder, JSONDecoder
        except ImportError:
            raise ImportError(
                "Cannot find an appropriate json module. Please easy_install "+\
                "simplejson and try again."
            )
'''
__all__ = [
    'Encoder',
    'json_encode',
    'json_decode',
    'JsonSerializable',
    'json_ensure_string_keys',
    'dehump',
    'hump',
    'Dictomatic',
]

class Encoder(json.JSONEncoder):

    def default(self, o):
        if hasattr(o, "json"):
            return getattr(o, "json")()
        if isinstance(o, datetime.datetime):
            return o.ctime()
        return JSONEncoder.default(self, o)

_encoder = Encoder()
def json_encode(o):
    return _encoder.encode(o)

_decoder = json.JSONDecoder()
def json_decode(o):
    # remove tabs if they exists
    o = o.replace('\t','')
    data = _decoder.decode(o)
    return data

class JsonSerializable(object):

    def json(self):
        # TODO: ugly
        d = {}
        for k, v in self.__dict__.iteritems():
            if isinstance(v, JsonSerializable):
                d[k] = v.json()
            elif v is not None:
                d[k] = v
        return d


def json_ensure_string_keys(json):
    return dict([(str(k), v) for k,v in json.items()])

camel_case = re.compile('([a-z]+[A-Z])')
skyline_case = re.compile('([a-z]+_[a-z])')

def dehump(match):
    result = ''
    for group in match.groups():
        result = result + group[0:len(group)-1]+"_"+group[len(group)-1].lower()
    return result

def hump(match):
    result = ''
    for group in match.groups():
        result = result + group[0:len(group)-2]+group[len(group)-1].upper()
    return result


class Dictomatic(dict):

    @classmethod
    def wrap(cls, data, decode=True, start=True):
        if isinstance(data, Dictomatic):
            return data
        if decode and isinstance(data, (types.StringType, types.UnicodeType)):
            data = json_decode(data)
        if not start and isinstance(data, (types.ListType, types.TupleType)):
            for index, value in enumerate(data):
                if isinstance(value, (types.DictType,
                                      types.ListType,
                                      types.TupleType)):
                    data[index] = Dictomatic.wrap(
                        value, decode=False, start=False
                    )
            return data
        elif isinstance(data, types.DictType):
            data = json_ensure_string_keys(data)
            for key, value in data.iteritems():
                if isinstance(value, (types.DictType,
                                      types.ListType,
                                      types.TupleType)):
                    data[key] = Dictomatic.wrap(
                        value, decode=False, start=False
                    )
            return Dictomatic(data)
        elif isinstance(data, types.NoneType):
            return Dictomatic({})
        else:
            raise ValueError('Unexpected type: %s' % type(data))

    def __getattr__(self, name, default=None):
        '''
        Makes a dictionary behave like an object with magic dehumping action.
        '''

        # try it normally
        try:
            return self[name]
        except KeyError:
            if name.startswith('__'):
                raise AttributeError()
            # try it humped, so camel_case_is_awesome => camelCaseIsAwesome
            try:
                return self[skyline_case.sub(hump, name)]
            # it's really not here, let them know
            except KeyError:
                try:
                    return self[camel_case.sub(dehump, name)]
                # it's really not here, let them know
                except KeyError:
                    return default

    def __setattr__(self, name, value):
        self[name] = value

