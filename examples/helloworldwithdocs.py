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

It is recommended to use a class or module for each logical section of your app.
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
from nudge.automagic.gen import Project, ProjectSection
from nudge.automagic.generate.stubs import PythonStubs

class ExampleException(Exception): pass

def handle_example_exception(e):
    return 400, 'application/json', '{"exception":"bad request"}', None

module_service_description = [
    Endpoint(name='Index',
        method='GET',
        uri='/$',
        function="index",
        renderer=HTML(),
    ),
    Endpoint(name='Post Hello',
        method='POST',
        uri='/hello/?$',
        function="say_hello",
        args=Args(
            args.JsonBodyField('name'),
        ),
    ),
    Endpoint(name='Put Hello',
        method='PUT',
        uri='/hello/(?P<name>[^/]+)?$',
        function="say_hello",
        args=Args(
            args.String('name'),
        ),
    ),
    Endpoint(name='Get Hello',
        method='GET',
        uri='/hello/?$',
        function="say_hello",
        args=Args(
            args.String('name'),
            args.Integer('number', optional=True),
        ),
    ),
    Endpoint(name='I just break',
        method='GET',
        uri='/break/?$',
        function="just_throw_an_exception",
        args=Args(),
        exceptions={
            ExampleException: handle_example_exception,
        }
    ),
    Endpoint(name='I just break',
        method='GET',
        uri='/break_fallback/?$',
        function="just_throw_an_exception",
        args=Args(),
    ),
    Endpoint(name='I throw an assertion exception',
        method='GET',
        uri='/break_assertion/?$',
        function="assert_false",
        args=Args(),
    )
]

'''
class_service_description = [
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
'''

if __name__ == "__main__":
     # Prep all the app's sections
    '''
    ProjectSection(
        name="HelloWorld Class Section",
        identifier="hello_world_class_section",
        description="HelloWorld Class example section",
        endpoints=class_service_description,
        options=None,
    ),
    '''
    sections = [
        ProjectSection(
            name="HelloWorld Module Section",
            identifier="hello_world_module",
            description="HelloWorld Module example section",
            endpoints=module_service_description,
            options=None,
        )
    ]
    # This will generate all docs/clients
    project = Project(
        name="HelloWorld Example",
        identifier="hello_world",
        description="HelloWorld Example description",
        sections=sections,
        destination_dir="/tmp/hello_world_gen/",
        generators=[PythonStubs(module='helloworld')]
    )

