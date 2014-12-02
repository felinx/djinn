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
import functools
from tornado.escape import to_unicode
from djinn import errors


class Validator(object):

    """Basic Validator class"""
    _error_message = "%s is an invalid param"

    def __init__(self, param, default=None, message=None, code=400):
        self.param = param
        self.default = default
        self.message = message
        self.code = code

        def _validate(func):
            @functools.wraps(func)
            def __validate(handler, *args, **kwargs):
                # validate handler.arguments
                self.handler = handler
                self.validate()
                return func(handler, *args, **kwargs)

            return __validate
        self._validate = _validate

    def __call__(self, *args, **kwargs):
        return self._validate(*args, **kwargs)

    def validate(self):
        raise NotImplementedError()

    @property
    def get_argument(self):
        return self.handler.get_argument

    def handle_error(self, param, *args):
        _ = self.handler.locale.translate
        args_ = [_(param), ]
        args_.extend(args)
        args = tuple(args_)

        if not self.message:
            message = _(self._error_message) % args
        else:
            if "%s" in self.message:
                message = _(self.message) % args
            else:
                message = _(self.message)

        raise errors.HTTPError(self.code, message)


class Required(Validator):
    _error_message = "%s is required"

    def __init__(self, param, message=None, code=400):
        super(Required, self).__init__(param, None, message, code)

    def validate(self):
        value = self.get_argument(self.param, None)
        if not value:
            self.handle_error(self.param)


class String(Validator):
    _error_message = "%s's length is invalid(%s-%s)"

    def __init__(self, param, default="", message=None,
                 max_len=200, min_len=0, as_unicode=True, code=400):
        self.max_len = max_len
        self.min_len = min_len
        self.as_unicode = as_unicode
        super(String, self).__init__(param, default, message, code)

    def validate(self):
        value = self.get_argument(self.param, self.default)
        if self.as_unicode:
            length = len(to_unicode(value))
        else:
            length = len(value)

        if length < self.min_len or length > self.max_len:
            self.handle_error(self.param, self.min_len, self.max_len)


class PlainText(String):
    _error_message = "%s is an invalid plain text(a-z, A-Z,0-9 and _)"

    def __init__(self, param, default="", message=None,
                 max_len=200, min_len=0, code=400):
        super(PlainText, self).__init__(param,
                                        default, message, max_len, min_len, code)
        self.regex = re.compile('^[a-zA-Z0-9_]{%d,%d}$' %
                                (self.min_len, self.max_len), re.IGNORECASE)

    def validate(self):
        value = self.get_argument(self.param, self.default)
        if not self.regex.match(value):
            self.handle_error(self.param)

        super(PlainText, self).validate()


class Integer(Validator):
    _error_message = "%s should be integer"

    def __init__(self, param, default=0, message=None, code=400):
        super(Integer, self).__init__(param, default, message, code)

    def validate(self):
        try:
            int(self.get_argument(self.param, self.default))
        except Exception:
            self.handle_error(self.param)


class Enum(Validator):
    _error_message = "%s should be in %s"

    def __init__(self, param, type_=None, enum=None, default=None, message=None, code=400):
        self.enum = enum if enum else ()
        self.type_ = type_
        super(Enum, self).__init__(param, default, message, code)

    def validate(self):
        value = self.get_argument(self.param, self.default)

        if self.type_:
            try:
                value = self.type_(value)
            except TypeError:
                # ingore type error
                pass

        if value not in self.enum:
            # try type detection
            for e in self.enum:
                e_type = e.__class__
                try:
                    if e_type(value) == e:
                        break
                except:
                    continue
            else:
                self.handle_error(self.param, self.enum)


class Regex(Validator):
    _error_message = "%s is invalid"

    def __init__(self, param, regex, flags=re.IGNORECASE, default="",
                 message=None, code=400):
        self.regex = re.compile(regex, flags)
        super(Regex, self).__init__(param, default, message, code)

    def validate(self):
        value = self.get_argument(self.param, self.default)
        if not self.regex.match(value):
            self.handle_error(self.param)


class Email(Regex):
    _error_message = "%s is an invalid email address"

    def __init__(self, param, message=None, code=400):
        # borrow email re pattern from django
        regex =  r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*" \
            r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"' \
            r")@(?:[A-Z0-9]+(?:-*[A-Z0-9]+)*\.)+[A-Z]{2,6}$"
        flags = re.IGNORECASE
        default = ""

        super(Email, self).__init__(param, regex,
                                    flags, default, message, code)


required = Required
string = String
integer = Integer
enum = Enum
regex = Regex
email = Email
plaintext = PlainText
