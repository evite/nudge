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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  
# 02110-1301  USA

"""
A more complicated example: A mini cms implementation designed 
to run using Google App Engine.

The aim of this example is to show how you would/could support multiple 
types of content, and handle error cases differently.
"""

import nudge.arg as args
from nudge import Endpoint, Args
from nudge.renderer import HTML, Result
from nudge.publisher import ServicePublisher

from google.appengine.api import users
from google.appengine.ext import db

# ---------------------------------------------------------------------------- #
# CMS Exceptions. It is a good idea to make your exceptions specific to
# the application you are implementing instead of being HTTP related.
# Later we will map these exceptions to HTTP status codes.

# TODO:
# Renderer for standard page view using an object
# Renderer for post page for redirecting if not logged in
## And for the view after the post
#

NotFoundPage = """
<html>
    <head><title>404 not found</title></head>
    <body>%s</body>
</html>"""


class UnauthorizedError(Exception):
    pass

class ContentNotFoundError(Exception):
    """ 
        Connection to persistent storeage was successful, but nothing was found
    """
    def __init__(self, msg):
        self.msg = msg
        self.response = response
        Exception.__init__(self, "Content %d: %s" % (code, msg))

class PageRender(object):
    """ A custom nudge renderer for handling error conditions as well as
        returning the proper content type from the stored page. """
    def __call__(self, page):
        # Something went wrong, we only have a string, just return it
        # In a real application, you would do something smarter.
        if isinstance(page, basestring):
            return Result(
                content=NotFoundPage % (page),
                content_type="text/html",
                http_status=404,
            )
        elif isinstance(page, object):
            return Result(
                content=page.content,
                content_type=page.content_type,
                http_status=200,
            )
        else:
            return Result(
                content="Server Error",
                content_type="text/plain",
                http_status=500,
            )



class ContentService(object):
    ADMIN_USERS = (
        "warren.runk@gmail.com",
    )
    CONTENT_TYPES = {
        "Json": "application/json",
        "Javascript": "application/javascript",
        "HTML": "text/html",
        "Plain": "text/plain",
        "CSS": "text/css",
    }


    def __init__(self):
        # Object Storage
        # Settings for
        ### Database Type
        ### Cache timing
        ### Static File caching
        pass

    def get_page(self, name, full_page=False):
        """ Overly simple page fetching function. This will try to look up
            the provided page_name, or raise an exception. full_page 
            determines whether or not we should attach a header and
            footer.
        """
        try:
            page = Page.get(name)
        except:
            page = "NOT FOUND"
        return page
        
    def save_page(self, user, name, content, content_type):
        """ """
        # Since this example is actually on appengine, I want to make sure
        # the person writing is authorized. In a real app you would likely 
        # want to abstract out user handling to an arg so it can work on
        # other frameworks
        # user = users.get_current_user()
        # if not user or user.email() not in self.ADMIN_USERS:
            # raise UnauthorizedError(
                # "Admin user required to change page content"
            # )

        page = Page.get(name)
        if not page:
            page = Page()

        # Page name is not changeable
        page.content = content
        page.content_type = content_type
        page._last_changer = user
        page.put()

class Page(db.Model):
    """ Simple page object for our cms example """
    name = db.StringProperty()
    content = db.TextProperty()
    content_type = db.StringProperty()
    # Auto set fields
    _creator = db.UserProperty()
    _last_changer = db.UserProperty()
    _create_datetime = db.DateTimeProperty(auto_now_add=True)
    _last_modified_datetime = db.DateTimeProperty(auto_now=True)

cs = ContentService()

service_description = [
    Endpoint(name='Get a Page',
        method='GET',
        uri='/(?P<name>.+)$',
        function=cs.get_page,
        args=Args(
            name=args.String('name'),
        ),
        renderer=HTML(),
    ),
    Endpoint(name='Store a Page',
        method='POST',
        uri='/(?P<name>.+)$',
        function=cs.save_page,
        args=Args(
            # user=args.GAEUser('user'),
            name=args.String('name'),
            content=args.String('content'),
        ),
        renderer=HTML(),
    ),
]

if __name__ == "__main__":
    # Options that serve() uses:
    #
    # --port= [default 8080]
    # --server=eventlet|tornado|paste|gae [default eventlet]
    # --threads= [only used with paste] [default 15]
    # --backlog= [only used with paste] [default 5 queued connections]
    # --greenthreads= [only used with eventlet] [default 100]
    # --debug=true|false [turns on colored debug logging] [default false]
    #
    sp = ServicePublisher(
        endpoints=service_description,
        debug=True,
    )
    from google.appengine.ext.webapp.util import run_wsgi_app
    run_wsgi_app(sp)

