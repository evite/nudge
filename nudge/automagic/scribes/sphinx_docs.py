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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import os

from nudge.automagic.scribes.default import DefaultGenerator, get_template
from nudge.utils import Dict, skyline_text

'''
    Sphinx does one index page, then a page for each method...
'''
class SphinxDocGenerator(DefaultGenerator):
    extension = 'rst'
    index_template = get_template('sphinx_index.txt')
    endpoint_template = get_template('sphinx_endpoint.txt')
    conf_template = get_template('sphinx_conf.txt')

    def _prepare_data(self, project):
        endpoints = {}
        sections = {}
        for section in project.sections:
            section_name = skyline_text(section.name)
            section_default = Dict({'name': section.name,
                                    'dir':section_name,
                                    'endpoints':[]})
            current_section = sections.setdefault(section_name, 
                                                  section_default)
            for ep in section.endpoints:
                name = skyline_text(ep.name)
                if name not in current_section.endpoints:
                    current_section.endpoints.append(name)
                desc = ep.function
                if callable(ep.function):
                    desc = ep.function.__doc__
                uri = self._fix_uri(project.domain + ep.uri)
                default_args = Dict({'file':name, 'dir':section_name,
                                     'args':[], 'uri':uri, 'name':ep.name, 
                                     'service':section.name, 'desc':desc,
                                     'http_method':ep.method, 
                                     'max_arg_name':len('Fields'),
                                     'max_arg_desc':len('Description'),
                                    })
                current = endpoints.setdefault(ep.function_name, default_args)
                current.args.extend(ep.sequential)
                current.args.extend(ep.named)
                for arg in current.args:
                    current.max_arg_name = \
                        max(current.max_arg_name, len(arg.name))
                    current.max_arg_desc = max(current.max_arg_desc, 
                                               len(self._build_arg_desc(arg)))
                
        return Dict({'project_name':project.name,
                     'copyright_year':'2011',
                     'company':'test company',
                     'version':'1.0',
                     'release':'1',
                     'htmlhelp_basename':'test_basename_help',
                     'sections': sections.values(), 
                     'endpoints':endpoints.values()})

    def _build_arg_desc(self, arg):
        desc = arg.__doc__ or '' 
        desc_lines = [d.strip() for d in desc.splitlines()]
        return ' '.join(desc_lines)

    def _fix_uri(self, uri):
        uri = "(?P<name>[^/]+)?$"
        blah = ">.*)"
        blah1 = "(?P<"
        return uri

    def _build_arg_table_items(self, endpoint):
        columns = ['Fields', 'Required', 'Description']
        separators = []
        separators.append("="*endpoint.max_arg_name)
        separators.append("="*len('Required'))
        separators.append("="*endpoint.max_arg_desc)
        args = []
        endpoint.arg_table_column_headers = ' '.join(columns)
        endpoint.arg_table_separator = ' '.join(separators)
        for arg in endpoint.args:
            field = arg.name
            field += " "*(endpoint.max_arg_name-len(field))
            required = " "*(len('Required'))
            if arg.optional:
                required = "x" + " "*(len('Required')-1)
            desc = self._build_arg_desc(arg)
            arg_desc = ' '.join([field, required, desc])
            print arg_desc
            args.append(arg_desc)
        endpoint.arg_strings = args

    def generate(self, project):
        data = self._prepare_data(Dict(project))
        # There is a listing of Sections and their endpoints in the index
        source_dir = self.dir + '/source'
        if not os.path.exists(source_dir):
            os.makedirs(source_dir)
        # Sphinx needs a conf.py to generate
        filename = self._filepath('conf', subdir='source', extension='py')
        self._render_and_write(self.conf_template, data, filename)
        # Sphinx needs an index.rst
        filename = self._filepath('index', subdir='source')
        self._render_and_write(self.index_template, data, filename)

        # Then there is one file for each endpoint (endpoint_name.rst)
        for endpoint in data.endpoints:
            self._build_arg_table_items(endpoint)
            filename = self._filepath(skyline_text(endpoint.name), 
                                      subdir='source/'+endpoint.dir)
            self._render_and_write(self.endpoint_template, endpoint, filename)
        build_dir = self.dir + '/build'
        if not os.path.exists(build_dir):
            os.makedirs(build_dir)
        # Write the gen script
        filename = self._filepath('gen', extension='sh')
        file = open(filename, 'wr')
        gen_script = '#!/bin/bash\nsphinx-build -b html source/ build/'        
        file.write(gen_script)
        file.close()
        # Exec the Sphinx doc generation
        os.system('pushd %s; sh gen.sh; popd;' % (self.dir))

