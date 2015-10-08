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

from tornado import escape
from tornado.web import HTTPError

# HTTP status code
HTTP_OK = 200
ERROR_BAD_REQUEST = 400
ERROR_UNAUTHORIZED = 401
ERROR_FORBIDDEN = 403
ERROR_NOT_FOUND = 404
ERROR_METHOD_NOT_ALLOWED = 405
ERROR_INTERNAL_SERVER_ERROR = 500
# Custom error code
ERROR_WARNING = 1001
ERROR_DEPRECATED = 1002
ERROR_MAINTAINING = 1003
ERROR_UNKNOWN_ERROR = 9999

# default errors
_unknown_error = "unknow_error"
_unknown_message = "Unknown error"
_error_types = {400: "bad_request",
                401: "unauthorized",
                403: "forbidden",
                404: "not_found",
                405: "method_not_allowed",
                500: "internal_server_error",
                1001: "warning",
                1002: "deprecated",
                1003: "maintaining",
                9999: _unknown_error}

ERROR_MESSAGES = {400: "Bad request",
                  401: "Unauthorized",
                  403: "Forbidden",
                  404: "Not found",
                  405: "Method not allowed",
                  500: "Internal server error",
                  1001: "Warning",
                  1002: "Deprecated",
                  1003: "Maintaining",
                  9999: _unknown_message}


class DjinnError(Exception):
    pass


class DatastoreError(DjinnError):
    pass


class TemplateContextError(DjinnError):

    """Template context variable does not exist."""
    pass


class HTTPAPIError(HTTPError):

    """API error handling exception

    API server always returns formatted JSON to client even there is
    an internal server error.
    """

    def __init__(self, status_code=ERROR_UNKNOWN_ERROR, message=None,
                 error=None, data=None, *args, **kwargs):
        assert isinstance(data, dict) or data is None
        message = message if message else ""
        assert isinstance(message, basestring)

        super(HTTPAPIError, self).__init__(int(status_code),
                                           log_message=message, *args, **kwargs)

        self.error = error if error else \
            _error_types.get(self.status_code, _unknown_error)
        self.message = message if message else \
            ERROR_MESSAGES.get(self.status_code, _unknown_message)
        self.data = data if data is not None else {}

    def __str__(self):
        err = {"meta": {"code": self.status_code, "error": self.error}}

        if self.data:
            err["data"] = self.data

        if self.message:
            err["meta"]["message"] = self.message % self.args

        return escape.json_encode(err)
