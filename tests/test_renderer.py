import unittest
from nose.tools import raises

from nudge.renderer import Json
from nudge.error import SecurityException

class JsonRendererTest(unittest.TestCase):
    
    @raises(SecurityException)
    def test_list_throws_500(self):
        Json()([1,2,3])

    def test_dict(self):
        result = Json()({'test':'me'}).content
        assert result == '{"test": "me"}', result

