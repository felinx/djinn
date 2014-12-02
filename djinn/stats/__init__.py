# -*- coding: utf-8 -*-
#
# Copyright(c) 2013 lottouch.com
#
# @author: Felinx Lee <felinx.lee@gmail.com>
# Created on Dec 17, 2013
#

import time
import os
import traceback
import argparse
import logging
from tornado import escape
from tornado.options import define, options

STATS_TIME_UNIT_MINTUE = 60  # 1 minute
STATS_TIME_UNIT_HOUR = 3600  # 1 hour
STATS_TIME_UNIT_DAY = 24 * 3600  # 1 day
STATS_TIME_UNIT_WEEK = 7 * 24 * 3600  # 1 week

define("stats_db_sync_delay", 300, int, "Delay to make sure data complete")
define("stats_synclock_time", 600, int, "Lock time to finish sync")


class Stats(object):
    _stats_key_prefix = "stats"

    def __init__(self, name, stats_redis, stats_db):
        self.name = name
        self.redis = stats_redis
        self.db = stats_db
        self.message = None
        self._sync_timestamp = None

    def process(self, message):
        r = True
        try:
            self.stats(message)
        except Exception, e:
            logging.error(e)
            logging.error(traceback.format_exc())
            # result should be False for error processing
            r = False

        if r and self.ready_to_sync:
            try:
                lock = self.get_sync_lock()
                if lock:
                    self.sync_to_db()
                    self.release_sync_lock()
            except Exception, e:
                # ingore db sync error, just log it
                logging.error(e)
                logging.error(traceback.format_exc())

        return r

    def stats(self, message):
        raise NotImplemented()

    def sync_to_db(self):
        raise NotImplemented()

    @property
    def ready_to_sync(self):
        if self._sync_timestamp and \
            time.time() - self._sync_timestamp > options.stats_db_sync_delay:
            self._sync_timestamp = None
            return True
        else:
            return False

    def prepare_to_sync(self):
        self._sync_timestamp = time.time()

    def get_sync_lock(self):
        """Sync to db lock.

        To make sure only one worker to sync data to MySQL database.
        """
        key = "%s:%s:synclock" % (self._stats_key_prefix, self.name)
        r = self.redis.setnx(key, os.getpid())
        if r:
            self.redis.expire(key, options.stats_synclock_time)
            return True
        else:
            return False

    def release_sync_lock(self):
        self.redis.delete("%s:%s:synclock" % (self._stats_key_prefix,
                                              self.name))
        self._sync_to_db = False
