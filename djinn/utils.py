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

"""Utility library"""

import re
import random
import importlib
from tornado.web import url
from tornado.options import options
from tornado import escape
from torndb import Row

from djinn.errors import TemplateContextError

ALPHABET_FULL = '23456789abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ'
ALPHABET_LOWER_ONLY = '23456789abcdefghijkmnpqrstuvwxyz'


class Context(dict):

    """Template context container.

    A container which will return empty string silently if the key is not exist
    rather than raise AttributeError when get a item's value.

    It will raise TemplateContextError if debug is True and the key
    does not exist.

    The context item also can be accessed through get attribute.

    """

    def __setattr__(self, key, value):
        self[key] = value

    def __str__(self):
        return str(self)

    def __iter__(self):
        return iter(self.items())

    def __getattr__(self, key):
        """Get a context attribute.

        Raise TemplateContextError if the attribute not be set to
        avoid confused AttributeError exception when debug is True, or return ""

        """
        if key in self:
            return self[key]
        elif options.debug:
            raise TemplateContextError("'%s' does not exist in context" % key)
        else:
            return ""

    def __hasattr__(self, key):
        if key in self:
            return True
        else:
            return False


def load_url_handlers(handlers_root_module, handlers_modules,
                      prefix=""):
    """Load URL handlers

    ``handlers_root_module``: The root module of all of handlers
    ``handlers_modules``: A list of module which is the container of a
    suite of handlers
    ``prefix``: URL prefix
    """
    handlers = []
    for handlers_module in handlers_modules:
        module = importlib.import_module(".%s" %
                                         handlers_module, handlers_root_module)
        module_hanlders = getattr(module, "handlers", None)
        if module_hanlders:
            _handlers = []
            for handler in module_hanlders:
                try:
                    patten = r"%s%s" % (prefix, handler[0])
                    if len(handler) == 2:
                        _handlers.append((patten,
                                          handler[1]))
                    elif len(handler) == 3:
                        _handlers.append(url(patten,
                                             handler[1],
                                             name=handler[2])
                                         )
                    else:
                        pass
                except IndexError:
                    pass

            handlers.extend(_handlers)

    return handlers


def get_count(row):
    """Get count from a query result

    ``row``: Row object of a torndb query result
    """
    if row:
        count = row.c  # c as count by name convention
    else:
        count = 0

    return count


def get_column_values(rows, column=None):
    """Get all values of a column from a query result

    ``rows``: A list of Row object of a torndb query result
    ``column``: Column name which value will be collected
    """
    result = []
    if rows:
        for row in rows:
            if column:
                result.append(row.get(column, None))
            else:
                result.append(row.values()[0])

    return result


def pick_row_attrs(row, attrs):
    if not row or not isinstance(row, dict):
        return row

    row_ = Row()
    for name in attrs:
        row_[name] = row.get(name, None)

    return row_


def gen_uid(size=6, alphabet=ALPHABET_LOWER_ONLY):
    s = []
    # random part of uid
    for i in xrange(0, size):
        s.append(random.choice(alphabet))

    return "".join(s)


def dict_value_to_string(data):
    assert isinstance(data, dict), "data should be a dict"

    for k, v in data.iteritems():
        if isinstance(v, unicode):
            data[k] = escape.utf8(v)
        elif isinstance(v, dict):
            data[k] = escape.json_encode(v)
        else:
            data[k] = v

    return data


def parse_on_off(status, default="on"):
    if not status:
        return default

    return "on" if status == "on" else "off"


def shorten_content(content, length):
    content = content.strip(" \n\t")
    content = content if len(
        content) <= length else "%s..." % content[0:length - 3]
    return content


def compare_version(v_a, v_b):
    """compare version numbers

    normal cases:
    1.10.2 > 1.1.3
    1.2.1 < 1.2.2
    1.2.0000 = 1.2.0

    exception cases:
    1.2.1abc > 1.2.1
    None < 1.0
    "  " < 1.0
    """
    def normalize(v):
        vv = []
        v = escape.utf8(v)

        if v:
            for x in re.sub(r'(\.0+)*$', '', v).split("."):
                try:
                    x = int(x)  # 001 to 1
                    vv.append(x)
                except ValueError:
                    # may have characters in the tail sometimes
                    vv.append(x)

        return vv

    return cmp(normalize(v_a), normalize(v_b))
