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

from optparse import OptionParser

import nudge.arg as args

from nudge import serve, Endpoint, Args
from nudge.renderer import HTML

class StupidException(Exception): pass

class HelloWorldService():

    def index(self):
        """ Just a starting point for the example service """
        return """
<html>
<h1>Demo</h1>

<form action="/hello" method="get">
<input type="text" name="name" value="Joe"/>
<input type="submit" value="get"/>
</form>
</html>
"""

    def say_hello(self, name, number=0):
        """ Say hello """
        return "Hello %s" % name

    def just_throw_an_exception(self):
        raise StupidException("omg what did you do?")

hws = HelloWorldService()

service_description = [
    Endpoint(name='Index',
        method='GET',
        uri='/$',
        function=hws.index,
        renderer=HTML(),
    ),
    Endpoint(name='Post Hello',
        method='POST',
        uri='/hello/?$',
        function=hws.say_hello,
        args=Args(
            args.JsonBodyField('name'),
        ),
    ),
    Endpoint(name='Put Hello',
        method='PUT',
        uri='/hello/(?P<name>[^/]+)?$',
        function=hws.say_hello,
        args=Args(
            args.String('name'),
        ),
    ),
    Endpoint(name='Get Hello',
        method='GET',
        uri='/hello/?$',
        function=hws.say_hello,
        args=Args(
            args.String('name'),
            args.Integer('number', optional=True),
        ),
    ),
    Endpoint(name='I just break',
        method='GET',
        uri='/break/?$',
        function=hws.just_throw_an_exception,
        args=Args(),
        exceptions={
            StupidException: 400,
        }
    )
]


if __name__ == "__main__":
    serve(service_description)
