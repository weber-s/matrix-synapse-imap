# -*- coding: utf-8 -*-
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import logging
import imaplib

from collections import namedtuple
from twisted.internet import defer

logger = logging.getLogger(__name__)

class IMAPAuthProvider:
    def __init__(self, config, account_handler):
        self.account_handler = account_handler
        self.create_users = config.create_users
        self.server = config.server
        self.port = config.port

    @defer.inlineCallbacks
    def check_3pid_auth(self, medium, address, password):
        """ Handle authentication against thirdparty login types, such as email
            Args:
                medium (str): Medium of the 3PID (e.g email, msisdn).
                address (str): Address of the 3PID (e.g bob@example.com for email).
                password (str): The provided password of the user.
            Returns:
                user_id (str|None): ID of the user if authentication
                    successful. None otherwise.
        """
        # We support only email
        if medium != "email":
            defer.returnValue(None)

        # user_id is of the form @foo:bar.com
        email = address
        localpart = address.split("@", 1)[0]
        user_id = "@"+localpart+":"+"testmatrix.gresille.org"
        #localpart = user_id.split(":", 1)[0][1:]
        #email = '@'.join(user_id[1:].split(':'))

        logger.info("Trying to login as %s on %s:%d via IMAP", email, self.server, self.port)

        # Talk to IMAP and check if this email/password combo is correct
        try:
            logger.debug("Attempting IMAP connection with %s", self.server)
            M = imaplib.IMAP4_SSL(self.server, self.port)
            r = M.login(email, password)
            if r[0] == 'OK':
                M.logout()
        except:
            defer.returnValue(None)

        if r[0] != 'OK':
            defer.returnValue(None)

        # From here on, the user is authenticated

        # Bail if we don't want to create users in Matrix
        if not self.create_users:
            defer.returnValue(None)

        # Create the user in Matrix if it doesn't exist yet
        if not (yield self.account_handler.check_user_exists(user_id)):
            yield self.account_handler.register_user(localpart=localpart, emails=[email])

        defer.returnValue(user_id)


    @defer.inlineCallbacks
    def check_password(self, user_id, password):
        """ Attempt to authenticate a user against IMAP
            and register an account if none exists.

            Returns:
                True if authentication against IMAP was successful
        """
        if not password:
            defer.returnValue(False)

        # user_id is of the form @foo:bar.com
        localpart = user_id.split(":", 1)[0][1:]
        email = '@'.join(user_id[1:].split(':'))

        logger.debug("Trying to login as %s on %s:%d via IMAP", email, self.server, self.port)

        try:
            M = imaplib.IMAP4_SSL(self.server, self.port)
            r = M.login(email, password)
            if r[0] == 'OK':
                M.logout()
        except:
            defer.returnValue(False)

        if r[0] != 'OK':
            defer.returnValue(False)

        # From here on, the user is authenticated

        # Bail if we don't want to create users in Matrix
        if not self.create_users:
            defer.returnValue(False)

        # Create the user in Matrix if it doesn't exist yet
        if not (yield self.account_handler.check_user_exists(user_id)):
            yield self.account_handler.register_user(localpart=localpart, emails=[email])

        defer.returnValue(True)

    @staticmethod
    def parse_config(config):
        imap_config = namedtuple('_Config', 'create_users')
        imap_config.create_users = config.get('create_users', True)
        imap_config.server = config.get('server', '')
        imap_config.port = config.get('port', imaplib.IMAP4_SSL_PORT)
        return imap_config
