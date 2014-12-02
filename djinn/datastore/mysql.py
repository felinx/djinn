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

import time
import logging
import random
from torndb import Connection as BaseConnection
from tornado.options import options
from tornado import escape

from ..errors import DatastoreError

manager = None


def setup(datastore_pool):
    global manager

    if manager is None:
        manager = MysqlManager(datastore_pool)
    return manager


class MysqlManager(object):
    _datastore_pool = {}

    def __init__(self, datastore_pool):
        for k, v in datastore_pool.iteritems():
            MysqlManager._datastore_pool[k] = MysqlMSConnection(v[0], v[1])

    def __getattr__(self, instance):
        r = self._datastore_pool.get(instance, None)
        if not r:
            raise DatastoreError("Mysql %s instance does not exist"
                                 % instance)

        return r


class MysqlMSConnection(object):

    """Mysql master & slave connection

    Manage datastore connection instances, it selects master or slave instance
    according to SQL statement automatically.

    """

    def __init__(self, master, slaves):
        self.master = Connection(master)

        self._slave_conns = []
        for slave in slaves:
            self._slave_conns.append(Connection(slave))

    @property
    def query(self):
        return self.slave.query

    @property
    def get(self):
        return self.slave.get

    @property
    def execute(self):
        return self.master.execute

    @property
    def executemany(self):
        return self.master.executemany

    @property
    def insert(self):
        return self.slave.insert

    @property
    def update(self):
        return self.slave.update

    @property
    def slave(self):
        return random.choice(self._slave_conns)


class Connection(BaseConnection):

    def __init__(self, options):
        default_options = {
            "host": "localhost:3306",
            "database": "test",
            "user": None,
            "password": None,
            "charset": "utf8mb4",
            "max_idle_time": 7 * 3600,
            "connect_timeout": 0,
            "time_zone": "+8:00"
        }
        default_options.update(options)

        super(Connection, self).__init__(**default_options)

    def _execute(self, cursor, query, parameters, kwparameters):
        # Override default _execute to log executing info when log_query is on
        parameters_ = []
        for parameter in parameters:
            if isinstance(parameter, unicode):
                parameter = escape.utf8(parameter)
            parameters_.append(parameter)
        parameters = tuple(parameters_)

        if options.LOG_DB_QUERY:
            sql = query % parameters
            try:
                start = time.time()
                r = super(Connection, self)._execute(cursor, query, parameters,
                                                     kwparameters)
                elapse = time.time() - start
                logging.info("SQL executing elapse %s seconds on %s: %s",
                             elapse, self.host, sql)

                return r
            except Exception, e:
                logging.error("SQL: %s", sql)
                raise e
        else:
            return super(Connection, self)._execute(cursor, query, parameters, kwparameters)
