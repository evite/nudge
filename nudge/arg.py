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

import types
import nudge
import nudge.validator as validate
from nudge.utils import dehump

__all__ = [
    'Arg',
    'CustomArg',
    'String',
    'Boolean',
    'Date',
    'Json',
    'Integer',
    'ClientIp',
    'RequestHeader',
    'Action',
    'JsonBody',
    'JsonBodyField',
    'List',
    'Dict',
]

class Arg(object):

    def __init__(self, name, optional=False, default=None, validator=None):
        # Are these class members unnecessary when using the below func?
        self.name = name
        self.optional = optional
        self.validator = validator
        self.default = default
        def func(req, inargs):
            exists = False
            data = None
            msg = None
            # We should move this check into the Endpoint constructor
            if not self.validator:
                raise AttributeError(
                    "Arg has no validator for property: '%s'" % self.name
                )
            if req.arguments and self.name in req.arguments:
                exists = True
                data = req.arguments[self.name]
            elif inargs and self.name in inargs:
                exists = True
                data = inargs[self.name]
            # Default assumes optional=True
            if not data:
                if self.optional:
                    return self.default
                elif exists:
                    msg = " is required, exists, but is empty"
                else:
                    msg = " is required but does not exist"
                raise nudge.publisher.HTTPException(
                    400,
                    self.name + msg
                )
            # Query string args will come in list format, take the first.
            # Unless of course we are expecting a list from the json body.
            if type(data) in [types.ListType] and not isinstance(self, List):
                data = data[0]
            try:
                return self.validator(data)
            except (validate.ValidationError), e:
                msg = "invalid value for argument '%s': '%s'" % (
                    self.name,
                    data
                )
                if e.message:
                    msg += ': %s' % e.message
                    raise nudge.publisher.HTTPException(400, msg)
        self.argspec = func

class CustomArg(Arg):

    def __init__(self, name=None):
        if not name and hasattr(self, '__name__'):
            name = dehump(self.__name__)
        self.name = name
        pass

    def argspec(self):
        pass

class String(Arg):
    """ Standard unicode string. No size restrictions """

    def __init__(self, name, optional=False, max_len=None):
        validator = validate.NotEmpty()
        if optional:
            validator = validate.String()
        super(String, self).__init__(
            name,
            optional=optional,
            validator=validator
        )

class Dict(Arg):

    def __init__(self, name, min_=None, max_=None,
                 optional=False):
        super(Dict, self).__init__(
            name,
            optional,
            default=None,
            validator=validate.Dict(min_, max_)
        )

class List(Arg):

    def __init__(self, name, min_=None, max_=None,
                 optional=False):
        super(List, self).__init__(
            name,
            optional,
            default=None,
            validator=validate.List(min_, max_)
        )

class Boolean(Arg):

    def __init__(self, name, default=None, optional=False):
        super(Boolean, self).__init__(
            name,
            optional,
            default,
            validate.Boolean()
        )

class Date(Arg):

    def __init__(self, name, default=None, optional=False):
        super(Date, self).__init__(
            name,
            optional,
            default,
            validate.Date()
        )

class Json(Arg):

    def __init__(self, name, default=None, optional=False):
        super(Json, self).__init__(
            name,
            optional,
            default,
            validate.Json()
        )

class Integer(Arg):

    def __init__(self, name, min_=None, max_=None,
                 default=None, optional=False):
        super(Integer, self).__init__(
            name,
            optional,
            default,
            validate.Int(min_, max_)
        )

class ClientIp(CustomArg):

    def __init__(self):
        def func(req, inargs):
            client_ip = req.headers.get("X-Forwarded-For", "") or req.remote_ip
            if client_ip:
                # client, proxy1, proxy2, ...
                client_ip = client_ip.partition(",")[0].strip()
            return client_ip
        self.argspec = func

class RequestHeader(CustomArg):

    def __init__(self, header):
        def func(req, inargs):
            return req.headers.get(header)
        self.argspec = func

class Cookie(CustomArg):

    def __init__(self, cookie):
        def func(req, inargs):
            '''
            Right now just return the first item of the list
            (no support for multivalued cookies)
            '''
            cook = req.cookies.get(cookie)
            if cook and len(cook) >= 1:
                return cook[0]
            # Else we return None :)
        self.argspec = func

class Action(Arg):
    actions = [
        "add",
        "edit",
        "delete",
    ]
    validators = [validate.StringAlternatives(actions)]


class UploadedFile(CustomArg):

    def __init__(self, name):
        def func(req, inargs):
            f = req.files[name][0]
            return {
                'filename': f['filename'],
                'data': f['body'],
                'content_type': f['content_type'],
            }
        self.argspec = func


class Body(Arg):

    def __init__(self, name=None, optional=False):
        self.name = name
        self.optional = optional

    def argspec(self, req, inargs):
        if not req.body:
            if self.optional:
                return None
            else:
                raise nudge.publisher.HTTPException(
                    400,
                    "body is required"
                )
        return req.body


class JsonBody(CustomArg):
    """ Checks that there's a valid JSON message body, converts this into
        a dict. It optionally adds specified entries to the dict and
        ultimately returns it.

        Note: if the request is a POST or a PUT, and the content type is
        application/json, the json body will be decoded and added to the arg
        dict (so you dont need to use this, you can use normal args).

        You might use this in the case where you want the json body object
        as a single arg (maybe the body is very large)
    """
    def __init__(self, optional=False, extend={}):
        def func(req, inargs):
            if not req.body:
                if optional:
                    return None
                else:
                    raise nudge.publisher.HTTPException(
                        400,
                        "json body is not optional"
                    )
            json_body = _get_json_body(req)
            if extend:
                return dict(json_body, **extend)
            return json_body
        self.argspec = func


class JsonBodyField(CustomArg):
    """ DEPRECATED -

        Note: if the request is a POST or a PUT, and the content type is
        application/json, the json body will be decoded and added to the arg
        dict (so you dont need to use this, you can use normal args).
    """
    def __init__(self, fieldname, optional=False, validator=None):
        self.name = fieldname
        def func(req, inargs):
            try:
                val = _get_json_body(req)[fieldname]
                if validator:
                    validator(val)
                return val
            except (KeyError, TypeError):
                if not optional:
                    raise nudge.publisher.HTTPException(
                        400,
                        "json body does not contain '%s'" % fieldname
                    )
            return None
        self.argspec = func


def _get_json_body(req):
    """ decode and cache json body """

    if '_body_dict' in req.arguments:
        return req.arguments['_body_dict']

    if not req.body:
        return None

    try:
        body = nudge.json.json_decode(req.body)
        req.arguments['_body_dict'] = body # cache it
        return body
    except (ValueError):
        raise nudge.publisher.HTTPException(400, "body is not JSON")
