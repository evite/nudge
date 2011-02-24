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
]

class Arg(object):
    
    def __init__(self, name, optional=False, default=None, validator=None):
        self.name = name
        self.optional = optional
        self.validator = validator
        self.default = default
        def func(req, inargs):
            if not self.validator:
                raise AttributeError(
                    "Arg has no validator for property: '%s'" % self.name
                )
            body = _get_json_body(req)
            if self.name not in (body or {}) and self.name not in \
                (req.arguments or {}) and self.name not in (inargs or {}):
                if default:
                    return default
                elif self.optional:
                    return None
                else:
                    raise nudge.publisher.HTTPException(
                        400, 
                        "%s is required" % self.name
                    )
            data = None
            if self.name in (body or {}):
                data = body.get(self.name, self.default)
            elif self.name in (req.arguments or {}):
                data = req.arguments.get(self.name, self.default)
                if isinstance(data, types.ListType) and len(data) == 1:
                    data = data[0]
            elif self.name in (inargs or {}):
                data = inargs[self.name]
            if not data and not self.optional:
                raise nudge.publisher.HTTPException(
                    400, 
                    "%s is required" % self.name
                )
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

    def __init__(self):
        pass
    
    def argspec(self):
        pass

class String(Arg): 

    def __init__(self, name, optional=False):
        validator = validate.NotEmpty()
        if optional:
            validator = validate.String()
        super(String, self).__init__(
            name, 
            optional=optional, 
            validator=validator
        )

class Boolean(Arg):
    validator = validate.Boolean()

class Date(Arg):
    validator = validate.Date()

class Json(Arg):
    validator = validate.Json()

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

class JsonBody(CustomArg):
    """ Checks that there's a valid JSON message body, converts this into
        a dict. It optionally adds specified entries to the dict and
        ultimately returns it
       
        Note: if the request is a POST or a PUT, and the content type is
        application/json, the json body will be decoded and added to the arg
        dict (so you dont need to use this, you can use normal args).
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

    if not req.body or \
        not req.headers.get(
            "Content-Type", 
            '').startswith("application/json"):
        return None

    try:
        body = nudge.json.json_decode(req.body)
        req.arguments['_body_dict'] = body # cache it
        return body
    except (ValueError):
        raise nudge.publisher.HTTPException(400, "body is not JSON")

