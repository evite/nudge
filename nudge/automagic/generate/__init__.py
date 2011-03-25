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

__import__('pkg_resources').declare_namespace(__name__)

import os
from nudge.automagic.generate.templates import get_template

class AutomagicGenerator(object):
    extension = 'txt'
    template = get_template('default.html')

    def __init__(self, dir='.', module=None):
        self.dir = dir
        self.module = module

    def ensure_output_file(self, overwrite=False):
        filepath = os.path.join(self.dir,'%s.%s' % (self.module, self.extension))
        if not os.path.exists(filepath):
            return True
        if overwrite:
            os.remove(filepath)
            return True
        raise Exception("This module already exists.  Please remove it to continue")

    def generate(self, project):
        self.ensure_output_file()
        stuff = self.template.render({"project":project})
        print stuff




