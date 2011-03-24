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

"""
A simple hello world example that illustrates how easy it is to write
a web application using Nudge.

It is recommended to use a class for each logical section of your application.
So if you were making Evite, you would probably have a separate class for
Users, Events, Gallery, etc. These classes are usually implemented 
independently of anything HTTP related (and in different files).

You will notice our class methods accept and return regular Python variables.
This makes your service classes extremely portable, elegant, and easy to test.

The service_description is where the real magic happens. Each Endpoint
describes in detail one type of HTTP request the user of your application
might make. Endpoints are designed to handle request routing, 
input transformation and validation, error/exception handling, 
and output formatting.

Anything HTTP should be possible with Nudge, but you may need to write an
extension or two. See the simplecms example for some examples extending Nudge.
"""
import nudge.arg as args
from nudge import serve, Endpoint, Args
from nudge.renderer import HTML

class ExampleException(Exception): pass

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
        raise ExampleException("omg what did you do?")

    def assert_false(self):
        assert False, "False can never be True"

hws = HelloWorldService()

def handle_example_exception(e):
    return 400, 'application/json', '{"exception":"bad request"}', None

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
            ExampleException: handle_example_exception,
        }
    ),
    Endpoint(name='I just break',
        method='GET',
        uri='/break_fallback/?$',
        function=hws.just_throw_an_exception,
        args=Args(),
    ),
    Endpoint(name='I throw an assertion exception',
        method='GET',
        uri='/break_assertion/?$',
        function=hws.assert_false,
        args=Args(),
    )
]

if __name__ == "__main__":
    serve(service_description)

