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
import json
import urlparse
import time
import logging

import oauth2 as oauth

_request_token_url = 'http://twitter.com/oauth/request_token'
_access_token_url = 'http://twitter.com/oauth/access_token'
_authorize_url = 'http://twitter.com/oauth/authorize'

_ROOT = 'http://api.twitter.com'
_VERS = '1'
_URLS = {
    'home_timeline': "statuses/home_timeline.json",
    'mentions': "statuses/mentions.json",
    'friends_timeline': "statuses/friends_timeline.json",
    'direct_messages': "direct_messages.json",
}

class ApiException(Exception): pass


class ApplicationClient(object):

    def __init__(self, key, secret):
        self._key = key
        self._secret = secret

        self._consumer = oauth.Consumer(key=self._key, secret=self._secret)
        self._client = oauth.Client(self._consumer)

    def authorization_url(self):
        resp, content = self._client.request(_request_token_url, "GET")
        if resp['status'] != '200':
            raise ApiException("Invalid response %s: %s" % (resp['status'], content))

        request_token = dict(urlparse.parse_qsl(content))
        return "%s?oauth_token=%s" % (_authorize_url, request_token['oauth_token'])

    def callback(self, oauth_token, verifier):
        token = oauth.Token(oauth_token, self._secret)
        token.set_verifier(verifier)

        client = oauth.Client(self._consumer, token)
        resp, content = client.request(_access_token_url, "POST")
        if resp['status'] != '200':
            raise ApiException("Invalid response %s: %s" % (resp['status'], content))
        access_token = dict(urlparse.parse_qsl(content))
        return self.create_user_client(access_token)

    def create_user_client(self, access_token):
        return UserClient(self._consumer, access_token, self._secret)


class UserClient(object):

    def __init__(self, consumer, access_token, secret):
        self.access_token = access_token
        token = oauth.Token(self.access_token['oauth_token'], self.access_token['oauth_token_secret'])
        self._client = oauth.Client(consumer, token)

    def _get(self, resource):
        resp, content = self._client.request(
            "%s/%s/%s" % (_ROOT, _VERS, _URLS[resource]),
            "GET"
        )
        if resp['status'] != '200':
            raise ApiException("Invalid response %s: %s" % (resp['status'], content)) 

        return json.loads(content)
    
    def home_timeline(self): return self._get('home_timeline')

    def mentions(self): return self._get('mentions')

    def friends_timeline(self): return self._get('friends_timeline')

    def direct_messages(self): return self._get('direct_messages')

