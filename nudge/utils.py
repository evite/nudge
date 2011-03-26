import re

'''
    I'm a first class citizen dictionary.
'''
class Dict(dict):
    def __getattr__(self, attr):
        return self.get(attr, None)
    __setattr__= dict.__setitem__
    __delattr__= dict.__delitem__


'''
    Let's make ThisCoolName => this_cool_name
'''
camel_case = re.compile('([a-z]+[A-Z])')
def dehump(string):
    def fix_caps(match):
        result = ''
        for group in match.groups():
            result = result + group[0:len(group)-1]+"_"+group[len(group)-1].lower()
        return result
    return camel_case.sub(fix_caps, string)

skyline_case = re.compile('([a-z]+_[a-z])')
def hump(string):
    def fix_ribs(match):
        result = ''
        for group in match.groups():
            result = result + group[0:len(group)-2]+group[len(group)-1].upper()
        return result
    return skyline_case.sub(fix_ribs, string)

def build_class_name(string):
    if not string:
        return ''
    result = hump(string)
    return result[0].upper()+result[1:]

'''
    This will take something like:
        string = 'this.that.the_thing_that_does_stuff.other'
    and return:
        ('that', 'the_thing_that_does_stuff', 'other')
        or
        ('that', 'TheThingThatDoesStuff', 'other')
'''
def breakup_function_path(input, camel_case=True):
    package = ''
    class_name, dot, function_name = input.rpartition('.')
    if not function_name:
        function_name = class_name
        class_name = None
    if class_name:
        package, dot, class_name = class_name.rpartition('.')
        if camel_case:
            class_name = build_class_name(class_name)
    if package:
        garbage, dot, package = package.rpartition('.')
    return package, class_name, function_name
