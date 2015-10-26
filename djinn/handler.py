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
import traceback
import logging

from tornado import escape
from tornado.options import options
from tornado.web import RequestHandler as BaseRequestHandler, HTTPError
from djinn import errors
from djinn.utils import Context

REMOVE_SLASH_RE = re.compile(".+/$")


class BaseHandler(BaseRequestHandler):

    def prepare(self):
        self.remove_slash()
        self.prepare_context()
        self.traffic_threshold()

    def traffic_threshold(self):
        pass

    def prepare_context(self):
        self._context = Context()

    def remove_slash(self):
        if self.request.method == "GET":
            if REMOVE_SLASH_RE.match(self.request.path):
                # remove trail slash in path
                uri = self.request.path.rstrip("/")
                if self.request.query:
                    uri += "?" + self.request.query

                self.redirect(uri)

    def render_string(self, template_name, **kwargs):
        """Override default render_string, add context to template."""
        assert "context" not in kwargs, "context is a reserved word for \
                template context valuable."
        kwargs['context'] = self._context
        kwargs['url_escape'] = escape.url_escape

        return super(BaseHandler, self).render_string(template_name, **kwargs)

    def get_argument(self, name, default=BaseRequestHandler._ARG_DEFAULT, strip=True):
        value = super(BaseHandler, self).get_argument(name, default, strip)

        return escape.utf8(value) if isinstance(value, unicode) else value

    def get_int_argument(self, name, default=0):
        try:
            return int(self.get_argument(name, default))
        except ValueError:
            return default


class APIHandler(BaseHandler):

    def finish(self, chunk=None, message=None):
        _ = self.locale.translate
        if chunk is None:
            chunk = {}

        if isinstance(chunk, dict):
            chunk = {"meta": {"code": errors.HTTP_OK}, "data": chunk}

            if message:
                chunk["message"] = _(message)
        elif isinstance(chunk, errors.HTTPAPIError):
            chunk.message = _(chunk.message)
            chunk = str(chunk)

        callback = escape.utf8(self.get_argument("callback", None))
        if callback:
            self.set_header("Content-Type", "application/x-javascript")

            if isinstance(chunk, dict):
                chunk = escape.json_encode(chunk)

            self._write_buffer = [callback, "(", chunk, ")"] if chunk else []
            super(APIHandler, self).finish()
        else:
            self.set_header("Content-Type", "application/json; charset=UTF-8")
            super(APIHandler, self).finish(chunk)

    def write_error(self, status_code, **kwargs):
        try:
            exc_info = kwargs.pop('exc_info')
            e = exc_info[1]

            if isinstance(e, errors.HTTPAPIError):
                pass
            elif isinstance(e, HTTPError):
                e = errors.HTTPAPIError(e.status_code, message=e.log_message)
            else:
                e = errors.HTTPAPIError(errors.ERROR_INTERNAL_SERVER_ERROR)

            exception = "".join([ln for ln
                                 in traceback.format_exception(*exc_info)])

            if status_code == errors.ERROR_INTERNAL_SERVER_ERROR \
                    and not options.debug:
                self.send_error_mail(exception)
            logging.warning("Exception: %s", exception)

            self.clear()
            # always return 200 OK for API errors
            self.set_status(errors.HTTP_OK)
            self.set_header("Content-Type", "application/json; charset=UTF-8")
            self.finish(e)
        except Exception:
            logging.error(traceback.format_exc())
            return super(APIHandler, self).write_error(status_code, **kwargs)

    def send_error_mail(self, exception):
        """Override to implement custom error mail"""
        pass


class ErrorHandler(BaseHandler):

    """Default 404: Not Found handler."""

    def prepare(self):
        super(ErrorHandler, self).prepare()
        raise HTTPError(errors.ERROR_NOT_FOUND)


class APIErrorHandler(APIHandler):

    """Default API 404: Not Found handler."""

    def prepare(self):
        super(APIErrorHandler, self).prepare()
        raise errors.HTTPAPIError(errors.ERROR_NOT_FOUND)
