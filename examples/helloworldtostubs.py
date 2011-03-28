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
A simple hello world example that illustrates how easy it is to generate
python module/class/method stubs using Nudge.

It is recommended to use a class or module for each logical section of your app.
So if you were making Evite, you would probably have a separate class for
Users, Events, Gallery, etc. These classes are usually implemented 
independently of anything HTTP related (and in different files).

SO, when you're in startup mode, you can build your endpoints first
if you want to, but have the function be something of the form:
    module.class.function_name => 
    OR
    function_name =>
        default modulename with module level function of name function_name
    OR
    module..function_name => 
        module of given name with module level function of name function_name
    OR
    class_name.function_name =>
        default module will have class called class_name with function
        of name function_name

NOTICE BELOW:
    module_service_description:
        this..this
        im_another_class.say_hello
        this.the_talker.say_hello
    class_service_description:
        im_another_class.just_throw_an_exception

this example will output 2 modules:
    1) this
    2) helloworld

Take a look and see what methods ended up where and it'll help you
make sense of it all ;)

These combinations are across all the endpoints in all of your sections,
SO if you have this_module..that_function in Section "A" and also in
Section "B", there will only be one this_module created with one
function named that_function.

"""
import nudge.arg as args
from nudge import serve, Endpoint, Args
from nudge.renderer import HTML
from nudge.project import Project, ProjectSection
from nudge.automagic.scribe import PythonStubs

class ExampleException(Exception): pass

def handle_example_exception(e):
    return 400, 'application/json', '{"exception":"bad request"}', None

module_service_description = [
    Endpoint(name='Index',
        method='GET',
        uri='/$',
        function="this..index",
        renderer=HTML(),
    ),
    Endpoint(name='Post Hello',
        method='POST',
        uri='/hello/?$',
        function="im_another_class.say_hello",
        args=Args(
            args.JsonBodyField('name'),
        ),
    ),
    Endpoint(name='Put Hello',
        method='PUT',
        uri='/hello/(?P<name>[^/]+)?$',
        function="the_talker.say_hello",
        args=Args(
            args.String('name'),
        ),
    ),
    Endpoint(name='Get Hello',
        method='GET',
        uri='/hello/?$',
        function="this.the_talker.say_hello",
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

class_service_description = [
        Endpoint(name='I just break',
        method='GET',
        uri='/break/?$',
        function="im_another_class.just_throw_an_exception",
        args=Args(),
        exceptions={
            ExampleException: handle_example_exception,
        }
    ),
    Endpoint(name='I just break',
        method='GET',
        uri='/break_fallback/?$',
        function="im_another_class.just_throw_an_exception",
        args=Args(),
    ),
    Endpoint(name='I throw an assertion exception',
        method='GET',
        uri='/break_assertion/?$',
        function="im_another_class.assert_false",
        args=Args(),
    )
]

if __name__ == "__main__":
     # Prep all the app's sections
    sections = [
        ProjectSection(
            name="HelloWorld Class Section",
            identifier="hello_world_class_section",
            description="HelloWorld Class example section",
            endpoints=class_service_description,
            options=None,
        ),
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
        generators=[PythonStubs(filename='helloworld')]
    )

