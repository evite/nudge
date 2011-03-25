'''

 Copyright (C) 2011 Evite LLC

 This library is free software; you can redistribute it and/or
 modify it under the terms of the GNU Lesser General Public
 License as published by the Free Software Foundation; either
 version 2.1 of the License, or (at your option) any later version.

 This library is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 Lesser General Public License for more details.

 You should have received a copy of the GNU Lesser General Public
 License along with this library; if not, write to the Free Software
 Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

  Auto Generated Python for project
  {{ project.name }} - {{ project.identifier }}
  {{ project.description }}
'''

{% for section in project.sections %}

/*
 * Section {{ section.name }} - {{ section.indentifier }}
 * {{ section.description }}
 */ 

{% for ep in section.endpoints %}
def {{ ep.function_name }}({% for arg in ep.arg_list%}{{ arg.name }}{% if arg.optional %}={{ arg.default }}{% endif %}{% endfor %}):
    pass


{% endfor %}
{% endfor %}

