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
import sys
import re

__all__ = [
    "Project",
    "ProjectSection",
    "generate",
]

class Project(object):
    """ A class that will contain the project's endpoints, and some
        infomation about the project.
        
        The idea here is that you pass this object your project's
        endpoints as different section, and you give me a destination
        directory to write to.

        Ultimately we need a way to select one or more generation steps
        that will be taken (and files written) to the dest dir.
        Like clients or spynix docs etc
        """
    def __init__(self, name, identifier, description, sections, 
            destination_dir, generators):
        #
        self.name = name
        assert re.match("[_a-zA-Z]+[\w]*", identifier), \
            identifier + " is not a valid identifier"
        self.identifier = identifier
        self.description = description
        self.sections = sections
        self.destination = destination_dir
        assert isinstance(generators, list), "generators must be a list"
        self.generators = generators
        project_dict = {"name":self.name,"identifier":self.identifier,
                        "description":self.description,"sections":self.sections}
        [gen.generate(project_dict) for gen in self.generators]

    def generate(self):
        """ Your subclasses should override this method """
        pass

class ProjectSection(object):
    def __init__(self, name, identifier, description, endpoints, options=None):
        self.name = name
        assert re.match("[_a-zA-Z]+[\w]*", identifier), \
            identifier + " is not a valid identifier"
        self.identifier = identifier
        self.description = description
        self.endpoints = endpoints
        self.options = options
        self.prepare_data()

    def prepare_data(self):
        """ Copy and sanitize all useful data from the endpoints and
            options into friendlier locations """
        for ep in self.endpoints:
            # Function string
            if callable(ep.function):
                ep.function_name = ep.function.__name__
                ep.function_info = ep.function.__doc__ or ""
            elif isinstance(ep.function, str):
                ep.function_name = ep.function
                ep.function_info = ep.function
            # Combine args and inargs into a nice informative list
            ep.args_list = []
            for arg in ep.sequential:
                ep.args_list.append(arg)
            for name, arg in ep.named.items():
                ep.args_list.append(arg)

            for arg in ep.args_list:
                # Just make sure all standard properties exist
                if not hasattr(arg, "default"):
                    arg.default = None
                if not hasattr(arg, "optional"):
                    arg.optional = None
                if not hasattr(arg, "validator"):
                    arg.validator = None
                if arg.validator:
                    arg.validator_name = arg.validator.__name__
                    arg.validator_info = arg.validator.__doc__ or ""
                else:
                    arg.validator_name = ""
                    arg.validator_info = ""
                arg.info = arg.__doc__ or ""
            ep.renderer_name = ep.renderer.__class__.__name__
            ep.renderer_info = ep.renderer.__doc__ or ""
            # TODO exceptions and exception handlers...

class dd(dict):
    def __getattr__(self, attr):
        return self.get(attr, None)
    __setattr__= dict.__setitem__
    __delattr__= dict.__delitem__

def generate(args):
    exec "from %s import service_description" % (args[0])

    for endpoint in service_description:
        endpoint = dd(endpoint.__dict__)
        print endpoint.name
        print "=" * 30
        print 
        if endpoint.function.__doc__:
            print endpoint.function.__doc__
            print
        print "Method and URI"
        print "=" * 30
        print "%(method)s %(uri)s" % endpoint
        print 
        if endpoint.sequential or endpoint.named:
            print "Args"
            print "=" * 30
            for arg in endpoint.sequential:
                print "* " + (arg.name+': ' if hasattr(arg, 'name') else '') + str(arg.__doc__ or arg.__class__.__name__) 
            for arg in endpoint.named:
                print "* " + (arg.name+': ' if hasattr(arg, 'name') else '') + str(arg.__doc__ or arg.__class__.__name__) 
        print "\n\n"

def help(args):
    print "sorry no help yet"

cmds = {
    'help':help,
    'generate': generate
}

def main(args):
    if len(args) < 1 or args[0] not in cmds:
        print "Usage: gen ["+ ('|'.join(cmds.keys())) + "]"
        return sys.exit(1)
    cmds[args[0]](args[1:])

if __name__ == '__main__':
    main(sys.argv[1:])
