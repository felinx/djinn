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

import hashlib
import logging
import functools
import memcache
from tornado.escape import utf8
from tornado.options import define, options

define("cache_key_prefix", "", str, "cache key prefix to avoid key conflict")
define("cache_key_prefix_another", "", str,
       "another cache in different cache prefix, should be delete at the same time")
define("cache_enabled", True, bool, "whether cache is enabled")
manager = None


def cache(key=None, timeout=3600, args_as_key=True):
    def _wrapper(func):
        @functools.wraps(func)
        def __wrapper(self, *args, **kw):
            if not options.cache_enabled:
                return func(self, *args, **kw)
            _key = key_gen(key, func, args_as_key, *args, **kw)
            value = manager.get(_key)
            if not value:
                value = func(self, *args, **kw)
                if value:
                    manager.set(_key, value, timeout)

            return value
        return __wrapper

    return _wrapper


def delete(key):
    key_ = key
    if options.cache_key_prefix:
        key = "%s:%s" % (options.cache_key_prefix, key_)
    manager.delete(key)

    if options.cache_key_prefix_another:
        another_key = "%s:%s" % (options.cache_key_prefix_another, key_)
        if another_key != key:
            manager.delete(another_key)


def key_gen(key="", func=None, args_as_key=True, *args, **kw):
    assert key or func, "key and func must has one"
    if key:
        if args_as_key and "%s" in key:
            args_ = []
            for arg in args:
                if isinstance(arg, (basestring, unicode, int, long)):
                    args_.append(arg)
            key = key % tuple(args_)
    else:
        code = hashlib.md5()
        code.update("%s-%s" % (func.__module__, func.__name__))

        # copy args to avoid sort original args
        c = list(args[:])
        # sort c to avoid generate different key when args is the same
        # but sequence is different
        c.sort()
        c = [utf8(v) if isinstance(v, (basestring, unicode))
             else str(v) for v in c]
        code.update("".join(c))

        c = ["%s=%s" % (k, v) for k, v in kw.iteritems()]
        c.sort()
        code.update("".join(c))

        key = code.hexdigest()

    if options.cache_key_prefix:
        key = "%s:%s" % (options.cache_key_prefix, key)

    return key


def setup(servers, timeout=3):
    global manager

    if manager is None:
        manager = CacheManager(servers, timeout)
    return manager


def reconnect(func):
    @functools.wraps(func)
    def _wrapper(self, *args, **kwargs):
        try:
            r = func(self, *args, **kwargs)

            return r
        except Exception:
            logging.exception("memcache server closed!")
            self.close()

    return _wrapper


class CacheManager(object):

    def __init__(self, servers, timeout=3):
        self.servers = servers
        self.default_timeout = int(timeout)
        self._cache = memcache.Client(self.servers)

        logging.debug("Memcached start client %s" % servers)

    @property
    def cache(self):
        if self._cache is None:
            self._cache = memcache.Client(self.servers)

        return self._cache

    @reconnect
    def add(self, key, value, timeout=0):
        if isinstance(value, unicode):
            value = utf8(value)

        return self.cache.add(utf8(key), value,
                              timeout or self.default_timeout)

    @reconnect
    def get(self, key, default=None):
        val = self.cache.get(utf8(key))
        if val is None:
            return default
        else:
            if isinstance(val, basestring):
                return utf8(val)
            else:
                return val

    @reconnect
    def set(self, key, value, timeout=0):
        if isinstance(value, unicode):
            value = utf8(value)
        return self.cache.set(utf8(key), value,
                              timeout or self.default_timeout)

    @reconnect
    def delete(self, key):
        return self.cache.delete(utf8(key))

    @reconnect
    def get_many(self, keys):
        return self.cache.get_multi(map(utf8, keys))

    def close(self, **kwargs):
        try:
            self._cache.disconnect_all()
        except Exception:
            self._cache = None

    @reconnect
    def stats(self):
        return self.cache.get_stats()

    @reconnect
    def flush_all(self):
        self.cache.flush_all()


if __name__ == "__main__":
    setup(["127.0.0.1"])

    @cache()
    def test(a):
        return a

    a = test(1)
    key = key_gen("", test, 1)
    assert manager.get(key) == a
