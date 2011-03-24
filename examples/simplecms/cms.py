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
from nudge.renderer import HTML, Result, Redirect
from nudge.publisher import ServicePublisher
from nudge.automagic.gen import Project, ProjectSection
from nudge.automagic.generate.javascript import JSClient
from nudge.automagic.generate.sphinx import SphinxDocs

from google.appengine.api import users
from google.appengine.ext import db
from urllib import quote_plus
import logging
import sys

log = logging.getLogger("cmstest")

# ---------------------------------------------------------------------------- #
# Simple page templates
#
# Normally you would use a real template language
#
PAGE_BASE = """
<html>
    <head><title>%s</title></head>
    <body>%s</body>
</html>"""

FORM = """
        <br/><br/>
        <form method="POST">
            %s
            Page Title
            <input id="title" name="title" type="text" value="%s"/><br/>
            Content<br/>
            <textarea id="content" name="content">%s</textarea><br/>
            <input type="submit" value="Save Page">
        </form>"""
CREATE_INPUT = 'Page Name<input id="name" name="name"/><br/>'
# ---------------------------------------------------------------------------- #
# CMS Application Exceptions
#
# It is a good idea to make your exceptions specific to
# the application you are implementing instead of being HTTP related.
#
class UnauthorizedError(Exception):
    def __init__(self, message, uri=None, form_data=None, not_possible=False):
        self.message = message
        self.uri = uri
        self.form_data = form_data
        self.not_possible = not_possible

class PageNotFoundError(Exception):
    pass

# ---------------------------------------------------------------------------- #
# CMS Nudge Error Handlers
# 
# Nudge allows you to specify a default error handler, and handlers for
# different exception types. Sometimes it makes sense to just use a default
# handler to handle all exceptions. In our case we will handle 
# UnauthorizedErrors differently.
#
class DefaultErrorHandler(object):
    """ The default class members directly below are the catch all defaults
        in case something really bad happens, and we cannot properly handle our
        error situation. They are saved by Nudge when the ServicePublisher is
        initialized. 
        
        This is the CMS application's default error handler that we will provide
        as a service publisher option 
        
        All Nudge error handlers are expected to return an ordered tuple of:
            - (int) HTTP Status code (must be a valid status code) 
            - (byte string) HTTP content type header
            - (byte string) HTTP content
            - (dict) HTTP headers dictionary
        
    """
    code = 500
    content_type = "text/html; charset=UTF-8"
    content = PAGE_BASE % (
        "Cms Test - 500 - Internal Server Error",
        "Internal Server Error"
    )
    headers = {}
    def __call__(self, exception):
        if isinstance(exception, PageNotFoundError):
            code = 404
            content = PAGE_BASE % (
                "Cms Test - 404 - Not Found",
                "The requested page could not be found " + \
                "<a href=\"/\">Home Page</a>"
            )
        else:
            # Log the exception trace since we are not expecting this error
            log.exception(exception)
            code = self.code
            content = self.content
        return (code, self.content_type, content, self.headers)

class AuthErrorHandler(DefaultErrorHandler):
    """ Handle any authentication errors here.
        We will map this handler to UnauthorizedError in our endpoints """

    def __call__(self, exception):
        if isinstance(exception, UnauthorizedError):
            if exception.not_possible:
                log.exception(exception)
                # They are logged in, but are not an admin
                code = 403
                content = PAGE_BASE % (
                    "Cms Test - 403 - Unauthorized",
                    "You are not authorized to perform this action "
                )
            else:
                # They are not logged in. Redirect to login page. This is a
                # pretty dumb way to handle a login redirection. In a real
                # app you should make them login before allowing such a post,
                # or save the post data some where temp.
                code = 302
                nudge_redirect = Redirect()
                result = nudge_redirect(exception.uri)
                return (result.http_status, result.content_type, 
                        result.content, result.headers)
        else:
            code = self.code
            content = self.content
        return (code, self.content_type, content, self.headers)

# ---------------------------------------------------------------------------- #
# Custom Nudge Renderer
# 
# Nudge provides a number of builtin renderer for various content types, but
# most applications will find they need to write a couple of their own
#
# Renderers are passed whatever the endpoint returned and are expected to return
# a valid HTTP result (Nudge Result object)
#
class PageRenderer(object):
    """ Our PageRenderer is very similar to nudge.renderer.HTML
        We do some simple template rendering, and figure out if should
        provide a create new view or not. """
    def __call__(self, page):
        # Something went wrong, we only have a string, just return it
        # In a real application, you would do something smarter.

        if not page:
            title = "Create a new page!"
            body  = title +"<br/><br/>"
            pages = Page.all()
            if pages:
                body += "Existing Pages:<br/>"
                body += "<ul>"
                for page in pages:
                    if page.name and page.title:
                        body += '<li><a href="/%s">%s</a></li>' % (
                            page.name, page.title
                        )
                body += "</ul><br/>"
            # Add the create form
            body += FORM % (
                CREATE_INPUT,
                "",
                ""
            )
        elif isinstance(page, Page):
            title = page.title
            body = page.title + "<br/><br/>" + page.content
            body += FORM % (
                "",
                page.title,
                page.content
            )
        else:
            raise Exception("Page Renderer takes a Page object or nothing")


        return Result(
            content=PAGE_BASE % (title, body),
            content_type="text/html; charset=utf-8",
            http_status=200,
        )
# ---------------------------------------------------------------------------- #
# CMS Page Service
#
# This service is designed to be HTTP-free. This will make your service code
# very portable, and much easier to test. 
# 
class PageService(object):
    ADMIN_USERS = (
        "example.user@test.com",
    )

    def get_page(self, name=""):
        """ Overly simple page fetching function. This will try to look up
            the provided page_name, or raise an exception.
        """
        if not name:
            return None
        # You would handle this in a better fashion in a real app :)
        if name.lower().startswith("favicon"):
            raise PageNotFoundError("%s Not found"%(name))
        # Try to get this page from the datastore. It would be better to
        # use cache and check there first.
        page = Page.all().filter("name = ", name).fetch(1)
        if page:
            return page[0]
        raise PageNotFoundError("Could not find page " + name)
        
    def save_page(self, admin_user, name, title, content):
        """ Notice how if we are creating a new page name will come from the
            POST body, but if this is an existing page, it will be taken from
            the uri. Nudge looks in various locations for parameters.
            
            This function should either raise an exception on failure, or 
            return a valid uri of the page to redirect to"""
        
        # Try to get this page from the datastore. It would be better to
        # use cache and check there first.
        page = Page.all().filter("name = ", name).fetch(1)

        if not page:
            # This page doesn't exist, create a new one!
            page = Page()
            page._creator = admin_user
            page.name = name
        else:
            page = page[0]

        # In a real app we would verify all input
        page.content = content
        page.title = title
        page._last_changer = admin_user
        # Also, you would check for deadline exceeded exceptions, etc.
        page.put()
        return name
# ---------------------------------------------------------------------------- #
# GAE Page Model
#
# This ties us directly to GAE. A real app should abstract...
#
class Page(db.Model):
    """ Simple page object for our cms example """
    name = db.StringProperty()
    title = db.StringProperty()
    content = db.TextProperty()
    # Auto set fields
    _creator = db.UserProperty()
    _last_changer = db.UserProperty()
    _create_datetime = db.DateTimeProperty(auto_now_add=True)
    _last_modified_datetime = db.DateTimeProperty(auto_now=True)

# ---------------------------------------------------------------------------- #
# GAE Custom Nudge Arg
#
class GAEAdminUser(object):
    """ We make our own custom arg that will make sure the user is logged
        in and is in our admin list.
        
        Most args make use of validators to do error checking of inputs
        received from the http request. In this case we are using a library
        (google's user) that wont make direct use of an input, so we will
        override the behavior of this arg to perform validation."""

    def __init__(self, name, admin_users):
        self.name = name
        def func(req, inargs):
            user = users.get_current_user()
            if not user: 
                raise UnauthorizedError(
                    message="GAE User not logged in",
                    uri=users.create_login_url("/"),
                )
            elif user.email() not in admin_users:
                raise UnauthorizedError(
                    "Admin user required to change page content",
                    not_possible=True,
                )
            return user
        self.argspec = func

# ---------------------------------------------------------------------------- #
# Setup the service description
#
# This is really the magic of nudge. The service description is designed to
# be easy to read and informative.
#
# Ideally you should separate this code from your pure python service code to
# increase portability. 
#
# Since the service_description is just a list, you can combine many 
# descriptions if you wish to run them in the same process. This will allow
# for quick reorganizing when trying to scale.
#
ps = PageService()
service_description = [
    Endpoint(name='Get a Page',
        method='GET',
        uri='/(?P<name>.+)?$',
        function=ps.get_page,
        args=Args(
            name=args.String('name', optional=True),
        ),
        # Our default exception handler will take care of any exceptions
        # this endpoint might throw.
        exceptions={},
        renderer=PageRenderer(),
    ),
    Endpoint(name='Save a Page',
        method='POST',
        uri='/(?P<name>.+)?$',
        function=ps.save_page,
        args=Args(
            admin_user=GAEAdminUser('admin_user', ps.ADMIN_USERS),
            name=args.String('name'),
            title=args.String('title'),
            content=args.String('content'),
        ),
        # Map the UnauthorizedError to its handler
        exceptions={
            UnauthorizedError:AuthErrorHandler()
        },
        renderer=Redirect(),
    ),
]

# ---------------------------------------------------------------------------- #
# Run the application
#
# As you can see here, what this all boils down to is creating a nice 
# wsgi application to be served by the python HTTP server of your choice
#
if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "-gen":
        # Prep all the app's sections
        sections = [
            ProjectSection(
                name="Cms HTML Section",
                identifier="cms_html_section",
                description="Cms HTML example section",
                endpoints=service_description,
                options=None,
            )
        ]
        # This will generate all docs/clients
        project = Project(
            name="Cms Example",
            identifier="cms",
            description="Cms Example description",
            sections=sections,
            destination_dir="/tmp/cms_gen/",
            generators=[SphinxDocs(), JSClient()]
        )
        sys.exit(0)

    wsgi_application = ServicePublisher(
        endpoints=service_description,
        # Enable colored (and more) logging
        debug=True,
        #
        # default_error_handler is a very important option as it changes the
        # what is returned when there is an unhandled exception. Nudge by
        # default will return HTTP code 500 with a simple json dict (type json)
        #
        options={"default_error_handler":DefaultErrorHandler()}
    )
    from google.appengine.ext.webapp.util import run_wsgi_app
    run_wsgi_app(wsgi_application)

