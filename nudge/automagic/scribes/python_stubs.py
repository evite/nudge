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

from nudge.automagic.scribes.default import DefaultGenerator, get_template
from nudge.utils import Dict, breakup_path

class PythonStubGenerator(DefaultGenerator):
    extension = 'py'
    template = get_template('python.txt')

    def _prepare_data(self, project):
        def arg_string(endpoint):
            args = []
            args.extend([arg_repr(arg) for arg in endpoint.sequential])
            args.extend([arg_repr(arg, True) for arg in endpoint.named])
            return ', '.join(args)

        def arg_repr(arg, named=False):
            if named:
                return '='.join([str(arg.name), str(None)])
            return arg.name
        modules = {}
        for section in project.sections:
            for ep in section.endpoints:
                # -- module_name and class_name can both be ''.  They'll be put
                # in the default module as simple functions
                # -- module_name..function_name means a module level function 
                # in the given module
                # -- something.otherthing = default module, something = 
                # class_name, otherthing = function_name
                # -- something = default module, module level function called 
                # something
                module, class_name, function = breakup_path(ep.function_name)
                current = (modules.setdefault(module,{})
                                 .setdefault(class_name, {})
                                 .setdefault(function, 
                                             Dict({'sequential':[],
                                                   'named':{}}))
                          )
                # Preserve order...it's super important
                if len(ep.sequential) > len(current.sequential):
                    current.sequential = ep.sequential
                func_desc = dict([(arg.name, arg) for arg in current.named])
                current.named.update(func_desc)
        del project['sections']
        module_list = []
        for module, classes in modules.iteritems():
            module_dict = Dict({
                'module_name':module,
                'classes':[],
                'project':project
            })

            for class_name, endpoints in classes.iteritems():
                data = [{'function_name':name, 'args':arg_string(args)} 
                        for name, args in endpoints.iteritems()]
                class_name = class_name or False
                class_desc = [{"name":class_name, "endpoints":data}]
                module_dict.classes.extend(class_desc)
            module_list.append(Dict(module_dict))
        return module_list

    def generate(self, project):
        module_list = self._prepare_data(Dict(project))
        for module in module_list:
            # functions without modules go into the default file
            output_file = self.output_file
            # otherwise they go into their specified module file
            if module.module_name:
                output_file = self._filepath(module.module_name)
            self._render_and_write(self.template, module, output_file)

