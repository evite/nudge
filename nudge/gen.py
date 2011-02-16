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
