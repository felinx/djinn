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

import redis
from ..errors import DatastoreError

manager = None


def setup(redis_pool):
    global manager

    if manager is None:
        manager = RstoreManager(redis_pool)
    return manager


class RstoreManager(object):
    _datastore_pool = {}

    def __init__(self, datastore_pool):
        for k, v in datastore_pool.iteritems():
            RstoreManager._datastore_pool[k] = redis.Redis(**v)

    def __getattr__(self, instance):
        r = self._datastore_pool.get(instance, None)
        if not r:
            raise DatastoreError("Redis %s instance does not exist"
                                 % instance)

        return r


class RedistoreException(Exception):
    pass
