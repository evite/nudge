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
