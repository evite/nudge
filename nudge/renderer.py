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

import base64
from cStringIO import StringIO
from nudge.json import json_encode
from nudge.error import HTTPException

__all__ = [
    'ExceptionRenderer',
    'Result', 
    'Json', 
    'Redirect',
    'CSS',
    'Img',
    'ImgToB64String',
    'ImgToString',
    'Binary',
    'HTML',
    'Ical',
    'Identity',
]

class Result(object):
    def __init__(self, content, content_type, http_status=200, headers=None):
        self.content = content
        self.content_type = content_type
        self.http_status = http_status
        if not headers:
            headers = {}
        self.headers = headers

class Json(object):
    """ Default Nudge HTTP Content Type. Encodes the entire endpoint
        result as json, and returns """

    def __call__(self, result):
        if result == None:
            raise HTTPException(404)
        return Result(
            content=json_encode(result),
            content_type='application/json; charset=UTF-8',
            http_status=200,
        )

class Redirect(object):
    def __init__(self, http_status=302):
        self.http_status = http_status

    def redirect(self, uri, http_status=302, headers=None):
        if headers:
            headers['Location'] = uri
        else:
            headers = {
                'Location': uri,
            }
        return Result(
            content="""
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
            content_type='text/html; charset=utf-8',
            headers=headers,
            http_status=http_status,
        )

    def __call__(self, uri, headers=None):
        return self.redirect(uri, self.http_status, headers)


class CSS(object):

    def __call__(self, content):
        return Result(
            content=content,
            content_type='text/css; charset=utf-8',
            http_status=200,
        )

class Img(object):

    # expects img.data, img.type
    def __call__(self, img):
        return Result(
            content=img.data,
            content_type="image" + img.type,
            http_status=200,
        )

class ImgOrRedirect(object):

    # expects {'img_url':url, 'data': img_data, 'content_type;: 'img/IMGTYPE'}
    def __call__(self, content):
        if content.data:
            return Result(
                content=content.data,
                content_type=content.content_type,
                http_status=200,
            )
        else:
            headers = {'Location': content.img_url}

            return Result(
                content="""
    <!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">
    <HTML>
    <HEAD>
    <TITLE>Moved</TITLE>
    </HEAD>
    <BODY>
    <H2>Moved</H2>
    <A HREF="%s">The requested URL has moved here.</A>
    </BODY>
    </HTML>""" % content.img_url,
                content_type='text/html; charset=utf-8',
                headers=headers,
                http_status=302,
            )
            
class ImgToB64String(object):
    
    def __call__(self, content):
        out = StringIO()
        content.save(out, format=content.format)
        return_string = out.getvalue()
        return_string = base64.b64encode(return_string)
        return Result(
            content=return_string,
            content_type='text/plain',
            http_status=200,
        )

class ImgToString(object):
    
    def __call__(self, content):
        out = StringIO()
        content.save(out, format=content.format)
        return_string = out.getvalue()
        return Result(
            content=return_string,
            content_type='image/'+content.format,
            http_status=200,
        )

class Binary(object):
    
    def __call__(self, content):
        return Result(
            content=content,
            content_type='',
            http_status=200,
        )

class HTML(object):

    def __call__(self, content):
        return Result(
            content=content,
            content_type='text/html; charset=utf-8',
            http_status=200,
        )

class Ical(object):

    def __call__(self, content, headers=dict()):
        headers["Content-disposition"] = "attachment; filename=event.ics"
        return Result(
            content=content,
            content_type='text/calendar;charset=ISO-8859-1',
            http_status=200,
            headers=headers,
        )

class Identity(object):
    """ returns the content with no further manipulation (eg. use to avoid the
        default JSONification """
    def __init__(self, content_type, http_status=200, headers=None):
        self.content_type = content_type
        self.http_status = http_status
        if not headers:
            headers = {}
        self.headers = headers

    def __call__(self, content):
        return Result(content, self.content_type, self.http_status,
            self.headers)

