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
import nudge
from nudge import Endpoint, Args, serve
from nudge.renderer import ExceptionRenderer, Result, Identity, Redirect

from examples.twitter.client import ApplicationClient, ApiException

import os
import json
import logging
import Cookie

try:
    from Crypto.Cipher import AES
    import base64

    BLOCK_SIZE = 32

    PADDING = '{'

    pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * PADDING

    secret = os.urandom(BLOCK_SIZE) # I'm not reusing so I don't care
    cipher = AES.new(secret)

    EncodeAES = lambda c, s: base64.b64encode(c.encrypt(pad(s)))
    DecodeAES = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(PADDING)
except:
    print "WARNING: ***********************************"
    print "WARNING: *     could not import AES        *"
    print "WARNING: * cookie stored in clear text!!!! *"
    print "WARNING: ***********************************"
    cipher = False
    EncodeAES = lambda c, s: s
    DecodeAES = lambda c, e: e


_key = os.getenv("TWITTER_KEY","__TWITTER_APP_KEY__")
_secret = os.getenv("TWITTER_SECRET","__TWITTER_SECRET__")

if _key == "__TWITTER_APP_KEY__":
    raise Exception("Please edit "+__file__+" to supply app keys")

app_client = ApplicationClient(_key, _secret)

class TwitterAuthException(Exception): pass

class UserTwitterClient(nudge.arg.CustomArg):
    
    def __init__(self):
        def func(req, inargs):
            try:
                cookies = req.headers.get('cookie')
                assert cookies
                c = Cookie.SimpleCookie()
                c.load(cookies)
                assert 'token' in c
                token = c['token']
                assert token
                request_token = json.loads(DecodeAES(cipher, token.value))
                return app_client.create_user_client(request_token)
            except (Exception), e:
                logging.exception('What?')
                raise TwitterAuthException()
        self.argspec = func

def handle_exception(e):
    headers = {
        'Set-Cookie':'token=',
    }
    return nudge.redirect(app_client.authorization_url(), headers)


class CallbackRedirect(Redirect):

    def __call__(self, token=None):
        """ This is not a good idea since anyone can steel this - but this is an example """
        if token:
            import Cookie
            c = Cookie.SimpleCookie()
            c['token'] = EncodeAES(cipher, json.dumps(token.access_token))
            headers = {
                'Set-Cookie':'token='+c['token'].coded_value
            }
        else:
            headers = {
                'Set-Cookie':'token=deleted; expires=Thu, 01-Jan-1970 00:00:01 GMT;'
            }
        return self.redirect('/', headers=headers)


def index(twitter_client, type=None):
    try:
        if not type:
            type = 'timeline'

        msgs = {
            'timeline': twitter_client.home_timeline,
            'mentions': twitter_client.mentions,
            'friends_timeline': twitter_client.friends_timeline,
        }[type]()
        html = "<html><head><title>Bad Twitter: %(type)s</title></head><body><h1>%(type)s</h1><ul>" % {'type': type }
        html += "<a href='/'>timeline</a> | "
        html += "<a href='/?type=mentions'>mentions</a> | "
        html += "<a href='/?type=friends_timeline'>friends</a> | "
        html += "<a href='/logout'>logout</a>"

        for msg in msgs:
            html += '<li><img src="%(image)s" /> %(user)s: %(text)s</li>' % {
                'image': msg['user']['profile_image_url'],
                'user': msg['user']['name'],
                'text': msg['text'],
            }
        html += "</ul></body></html>"
        return html
    except:
        logging.exception("What!?")
        return "<html>ERROR</html>"
    
def callback(oauth_token=None, oauth_verifier=None):
    if oauth_token and oauth_verifier:
        try:
            return app_client.callback(oauth_token, oauth_verifier)
        except:
            pass
    return []


service_description = [
    Endpoint(
        'index',
        'GET',
        '/$',
        index,
        args=Args(
            UserTwitterClient(),
            nudge.arg.String('type', optional=True),
        ),
        renderer=Identity('text/html'),
        exceptions={
            TwitterAuthException: handle_exception,
        },
    ),
    Endpoint(
        'logout',
        'GET',
        '/logout',
        callback,
        renderer=CallbackRedirect(),
    ),
    Endpoint(
        'oauth callback',
        'GET',
        '/oauth_callback',
        callback,
        args=Args(
            nudge.arg.String('oauth_token'),
            nudge.arg.String('oauth_verifier'),
        ),
        renderer=CallbackRedirect(),
    ),
]

if __name__ == '__main__':
    serve(service_description)

