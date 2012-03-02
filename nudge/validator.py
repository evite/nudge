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

import re
import functools
import types

import nudge.json2
import datetime

__all__ = [
    'ValidationError',
    'DateTime',
    'Date',
    'String',
    'NotEmpty',
    'Int',
    'Float',
    'StringAlternatives',
    'Boolean',
    'Json',
    'List',
    'Dict',
]

class ValidationError(BaseException):
    def __init__(self, message=None):
        self.message = message

def DateTime():
    date_re = re.compile(r'^\d{8}T\d{6}')
    def f(s):
        if not date_re.match(s):
            raise ValidationError("malformed, use eg. '20100527T100000'")

        return s
    return f

def Date():
    """convert a string (eg. '20100527' to a datetime.date"""

    date_re = re.compile(r'(\d{4})(\d{2})(\d{2})')
    def f(s):

        try:
            year, month, day = [ int(i) for i in date_re.match(s).groups()[0:3]]
            return datetime.date(year, month, day)

        except (ValueError, AttributeError), e:
            raise ValidationError("malformed, use eg. '20100527'")

    return f

def String():
    def f(s):
        if isinstance(s, (types.UnicodeType, types.StringType)):
            return s
        raise ValidationError("invalid: not a string")
    return f

def NotEmpty():
    def f(s):
        if not s:
            raise ValidationError("invalid: empty string")
        return s
    return f

def Int(min_=None, max_=None):
    def f(s):
        try:
            i = int(s)
        except (ValueError, TypeError):
            raise ValidationError("must be a number")
        if (min_ is not None and i < min_):
            raise ValidationError("must be >= %d" % min_)
        if (max_ is not None and i > max_):
            raise ValidationError("must be <= %d" % max_)

        return i
    return f

def List(min_=None, max_=None):
    def f(s):
        if not isinstance(s, list):
            raise ValidationError("must be of type list")
        if min_ and len(s) < min_:
            raise ValidationError("list length must be gte %i" % (min_))
        if max_ and len(s) > max_:
            raise ValidationError("list length must be lte %i" % (max_))
        return s
    return f

def Dict(min_=None, max_=None):
    def f(s):
        if not isinstance(s, dict):
            raise ValidationError("must be of type dict")
        if min_ and len(s) < min_:
            raise ValidationError("dict length must be gte %i" % (min_))
        if max_ and len(s) > max_:
            raise ValidationError("dict length must be lte %i" % (max_))
        return s
    return f

def Float(min_=None, max_=None):
    if min_ is not None:
        min_ = float(min_)
    if max_ is not None:
        max_ = float(max_)
    def f(s):
        try:
            v = float(s)
        except (ValueError, TypeError):
            raise ValidationError("must be a number")
        if (min_ is not None and v < min_):
            raise ValidationError("must be >= %d" % min_)
        if (max_ is not None and v > max_):
            raise ValidationError("must be <= %d" % max_)

        return v
    return f

def StringAlternatives(alt_list):
    for s in alt_list: # Just want to make sure they are strings
        assert isinstance(s, basestring)
    alt_set = set(alt_list)
    def f(s):
        if not s in alt_set:
            raise ValidationError("must be one of: %s" % (', '.join(alt_set)))

        return s
    return f

def Boolean():
    def f(s):
        if isinstance(s, basestring):
            s = s.lower().strip()
        if s in [ '1', 1, 'on', 'true', 't', True]:
            return True
        elif s in ['0', 0, 'off', 'false', 'f', False]:
            return False
        raise ValidationError("must be one of 0, 1, on, off, true or false")
    return f

def Json():
    def f(s):
        try:
            return nudge.json2.json_decode(s)
        except (ValueError), e:
            raise ValidationError("must be valid json")
    return f

