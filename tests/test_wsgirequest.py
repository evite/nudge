import unittest

import StringIO

from nudge.publisher import WSGIRequest

class WSGIRequestTest(unittest.TestCase):

    def test_xff_header(self):
        input = StringIO.StringIO()
        req = WSGIRequest({
            'REQUEST_METHOD':'POST',
            'REMOTE_ADDR':'127.0.0.1',
            'wsgi.input': input,
            'HTTP_X-Forwarded-For':'10.0.10.123',
        })
        print req.headers
        assert req.headers['X-Forwarded-For'] == '10.0.10.123'
        assert req.headers.get('X-Forwarded-For') == '10.0.10.123', req.headers.get('X-Forwarded-For')


    def test_xff_header_eventlet(self):
        input = StringIO.StringIO()
        req = WSGIRequest({
            'REQUEST_METHOD':'POST',
            'REMOTE_ADDR':'127.0.0.1',
            'wsgi.input': input,
            'HTTP_X_FORWARDED_FOR':'10.0.10.123',
        })
        print req.headers
        assert req.headers['X-Forwarded-For'] == '10.0.10.123'
        assert req.headers.get('X-Forwarded-For') == '10.0.10.123', req.headers.get('X-Forwarded-For')

