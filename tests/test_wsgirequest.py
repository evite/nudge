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

    def test_request_files(self):
        input = StringIO.StringIO('''
-----------------------------41184676334
Content-Disposition: form-data; name="caption"

Summer vacation
-----------------------------41184676334
Content-Disposition: form-data; name="upload"; filename="extra_data.txt"
Content-Type: text/plain

Some more data about my vacation
-----------------------------41184676334--
''')
        request = WSGIRequest({
            'REQUEST_METHOD': 'POST',
            'REMOTE_ADDR': '127.0.0.1',
            'CONTENT_TYPE': 'multipart/form-data; boundary=---------------------------41184676334',
            'wsgi.input': input,
        })

        args = request.arguments
        assert args['caption'] == 'Summer vacation'
        assert args['upload'] == 'Some more data about my vacation'
        assert len(request.files) == 1, 'should have parsed a single file'
        assert request.files['upload'].filename == 'extra_data.txt'
        assert request.files['upload'].value.strip() == 'Some more data about my vacation'
