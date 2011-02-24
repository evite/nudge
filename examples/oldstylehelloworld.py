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

"""
This is an example of how things are done using tornado.

This tends to lead to a lot of duplicated code.
"""


from optparse import OptionParser

from nudge.json import json_decode

import tornado.httpserver
import tornado.ioloop
import tornado.web

class HelloWorldService():

    def index(self):
        return """
                <html>
                <h1>Demo</h1>

                <form action="/hello" method="get">
                <input type="text" name="name" value="Joe"/>
                <input type="submit" value="get"/>
                </form>
                </html>
                """

    def post_hello(self, name):
        return "Hello %s" % name

    def put_hello(self, name):
        return "Hello %s" % name

    def get_hello(sef, name, number=0):
        if number:
            name = '%s %i' % (name, number)
        return "Hello %s" % name


hws = HelloWorldService()

class MainHandler(tornado.web.RequestHandler):

    def get(self):
        self.write(hws.index())

class HelloHandler(tornado.web.RequestHandler):

    def post(self, name=None):
        body = json_decode(self.request.body)
        name = body.get('name', None)
        if not name or not str(name).strip():
            raise tornado.web.HTTPError(500, "You must pass a name.")
        self.write(hws.post_hello(name))

    def put(self, name=None):
        if not name or not str(name).strip():
            raise tornado.web.HTTPError(500, "You must pass a name.")
        self.write(hws.put_hello(name))

    def get(self):
        name = self.get_argument('name', None)
        if not name or not str(name).strip():
            raise tornado.web.HTTPError(500, "You must pass a name.")
        number = self.get_argument('number', None)
        if number:
            try:
                number = int(number)
            except ValueError:
                raise tornado.web.HTTPError(500, "If you pass a number, it must be a number.")
                number = None
        self.write(hws.get_hello(name, number))

application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/hello/?", HelloHandler),
    (r"/hello/([^/]+)/?", HelloHandler),
])

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-p", "--port", dest="port", help="port to run on", default=8090)
    (options, args) = parser.parse_args()

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

