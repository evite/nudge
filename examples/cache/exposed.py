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
import nudge
from nudge import Endpoint, Args, serve
import memcache

mc = memcache.Client(['127.0.0.1:11211'], debug=0)

def index():
    return open("examples/cache/index.html").read()

service_description = [
    Endpoint(
        'index',
        'GET',
        '/$',
        index,
        renderer=nudge.renderer.HTML,
    ),
    Endpoint(
        'get',
        'GET',
        '/cache/(?P<key>.*)$',
        mc.get,
        args=Args(
            nudge.arg.String('key'),
        )
    ),
    Endpoint(
        'set',
        'POST',
        '/cache/(?P<key>.*)$',
        mc.set,
        args=Args(
            nudge.arg.String('key'),
            nudge.arg.String('value'),
        )
    ),
]

if __name__ == '__main__':
    serve(service_description)

