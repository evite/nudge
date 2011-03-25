/*

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

 * Auto Generated Javascript Client for project
 * {{ project.name }} - {{ project.identifier }}
 * {{ project.description }}
 */

function json_post(uri, data, sfun, efun){
    $.ajax({
        url: uri,
        type: "POST",
        dataType: "json",
        contentType: "application/json;charset=UTF-8",
        data: JSON.stringify(data),
        cache: false,
        async: true,
        success: sfun,
        error: efun
    });
}
function validate_int(input, min, max){
    if(!((input - 0) == input && input.length > 0)){
        return false;
    }
    input = input - 0;
    if( input <

    
}
var {{ project.identifier }} = {{ project.identifier }} || {};

{% for section in project.sections %}

/*
 * Section {{ section.name }} - {{ section.indentifier }}
 * {{ section.description }}
 */ 
{{ project.identifier }}.{{ section.identifier }} = {};


{% for ep in section.endpoints %}
{{ project.identifier }}.{{ section.identifier }}.{{ ep.function_name }} =
    function(){
        // Get params from the dom via jquery
        {% for arg in ep.arg_list %}
        // get arg from dom via jquery
        //verify arg
        // add arg to obj    
        {% endfor %}
    };


{% endfor %}
{% endfor %}

