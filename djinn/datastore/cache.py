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
from six import PY2, iteritems
from tornado.escape import utf8
from tornado.options import define, options

define("cache_key_prefix", "", str, "cache key prefix to avoid key conflict")
define("cache_enabled", True, bool, "whether cache is enabled")
manager = None

logger = logging.getLogger(__name__)


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


def key_gen(key="", func=None, args_as_key=True, *args, **kw):
    assert key or func, "key and func must has one"
    if key:
        if args_as_key and "%s" in key:
            args_ = []
            for arg in args:
                if PY2:
                    cls_tup = (basestring, unicode, int, long)
                else:
                    cls_tup = (str, bytes, int)
                if isinstance(arg, cls_tup):
                    args_.append(arg)
            key = key % tuple(args_)
    else:
        code = hashlib.md5()
        code.update("%s-%s-%s" % (func.__file__, func.__module__, func.__name__))

        # copy args to avoid sort original args
        c = list(args[:])
        # sort c to avoid generate different key when args is the same
        # but sequence is different
        c.sort()
        if PY2:
            cls_tup = (basestring, unicode)
        else:
            cls_tup = (str, bytes)
        c = [utf8(v) if isinstance(v, cls_tup)
             else str(v) for v in c]
        code.update("".join(c))

        c = ["%s=%s" % (k, v) for k, v in iteritems(kw)]
        c.sort()
        code.update("".join(c))

        key = code.hexdigest()
        
        # salt used to reduce the same key
        salt = func.__name__
        code.update(salt)
        key += code.hexdigest()[:3]

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
            ret = func(self, *args, **kwargs)

            return ret
        except Exception:
            logger.exception("memcache server closed!")
            self.close()

    return _wrapper


class CacheManager(object):

    def __init__(self, servers, timeout=3):
        self.servers = servers
        self.default_timeout = int(timeout)
        self._cache = memcache.Client(self.servers)

        logger.debug("Memcached start client %s" % servers)

    @property
    def cache(self):
        if self._cache is None:
            self._cache = memcache.Client(self.servers)

        return self._cache

    @reconnect
    def add(self, key, value, timeout=0):
        if PY2 and isinstance(value, unicode):
            value = utf8(value)

        return self.cache.add(key, value,
                              timeout or self.default_timeout)

    @reconnect
    def get(self, key, default=None):
        val = self.cache.get(key)
        if val is None:
            return default

        if PY2 and isinstance(val, basestring):
            return utf8(val)

        return val

    @reconnect
    def set(self, key, value, timeout=0):
        if PY2 and isinstance(value, unicode):
            value = utf8(value)
        return self.cache.set(key, value,
                              timeout or self.default_timeout)

    @reconnect
    def delete(self, key):
        return self.cache.delete(key)

    @reconnect
    def get_many(self, keys):
        return self.cache.get_multi(keys)

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
