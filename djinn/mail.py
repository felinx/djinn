# -*- coding: utf-8 -*-
#
# Copyright(c) 2014 palmhold.com
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import re
import logging
import smtplib
import time
from datetime import datetime, timedelta
from email import encoders
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import COMMASPACE
from email.utils import formatdate

from tornado.escape import utf8
from tornado.options import options

__all__ = ("send_email", "EmailAddress")

# borrow email re pattern from django
_email_re = re.compile(
    # dot-atom
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"
    # quoted-string
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"'
    r')@(?:[A-Z0-9]+(?:-*[A-Z0-9]+)*\.)+[A-Z]{2,6}$', re.IGNORECASE)  # domain


def send_email(fr, to, subject, body, html=None, attachments=[]):
    """Send an email.

    If an HTML string is given, a mulitpart message will be generated with
    plain text and HTML parts. Attachments can be added by providing as a
    list of (filename, data) tuples.
    """
    # convert EmailAddress to pure string
    if isinstance(fr, EmailAddress):
        fr = str(fr)
    else:
        fr = utf8(fr)
    to = [utf8(t) for t in to]

    if html:
        # Multipart HTML and plain text
        message = MIMEMultipart("alternative")
        message.attach(MIMEText(body, "plain"))
        message.attach(MIMEText(html, "html"))
    else:
        # Plain text
        message = MIMEText(body)
    if attachments:
        part = message
        message = MIMEMultipart("mixed")
        message.attach(part)
        for filename, data in attachments:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(data)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment",
                            filename=filename)
            message.attach(part)

    message["Date"] = formatdate(time.time())
    message["From"] = fr
    message["To"] = COMMASPACE.join(to)
    message["Subject"] = utf8(subject)

    _get_session().send_mail(fr, to, utf8(message.as_string()))


class EmailAddress(object):

    def __init__(self, addr, name=""):
        assert _email_re.match(addr), "Email address(%s) is invalid." % addr

        self.addr = addr
        if name:
            self.name = name
        else:
            self.name = addr.split("@")[0]

    def __str__(self):
        return '%s <%s>' % (utf8(self.name), utf8(self.addr))


class _SMTPSession(object):

    def __init__(self, host, user='', password='', duration=30, tls=False):
        self.host = host
        self.user = user
        self.password = password
        self.duration = duration
        self.tls = tls
        self.session = None
        self.deadline = datetime.now()
        self.renew()

    def send_mail(self, fr, to, message):
        if self.timeout:
            self.renew()

        try:
            self.session.sendmail(fr, to, message)
        except Exception, e:
            err = "Send email from %s to %s failed!\n Exception: %s!"
            logging.error(err, fr, to, e)
            self.renew()

    @property
    def timeout(self):
        if datetime.now() < self.deadline:
            return False
        else:
            return True

    def renew(self):
        try:
            if self.session:
                self.session.quit()
        except Exception:
            pass

        self.session = smtplib.SMTP(self.host)
        if self.user and self.password:
            if self.tls:
                self.session.starttls()

            self.session.login(self.user, self.password)

        self.deadline = datetime.now() + timedelta(seconds=self.duration * 60)


def _get_session():
    global _session
    if _session is None:
        _session = _SMTPSession(options.smtp['host'],
                                options.smtp['user'],
                                options.smtp['password'],
                                options.smtp['duration'],
                                options.smtp['tls'])

    return _session

_session = None
