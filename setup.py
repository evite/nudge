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

#
# Run "python setup.py bdist_egg" to create an "egg" distribution.
#

from setuptools import setup

setup(
    name='nudge',
    version='0.6.5',
    packages=[
        'nudge',
    ],
    namespace_packages = ['nudge'],
    install_requires=['simplejson>=2.1.3'],
    
    zip_safe=False,

    author = "Evite LLC",
    description = "Nudge",
)

