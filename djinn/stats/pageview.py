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

import logging
from . import Stats, STATS_TIME_UNIT_DAY
from tornado.options import define, options

define("stats_time_expire", (72 + 1) * 3600, int,
       "expire time for stats records")
define("stats_db_sync_max_units", 5, int,
       "Max time units will be tried to synced")
define("stats_db_sync_min_views", 5, int,
       "Min views will be synced")


class PageviewStats(Stats):
    _stats_key_prefix = "stats:pv"

    def __init__(self, name, stats_redis, stats_db,
                 stats_time_unit=STATS_TIME_UNIT_DAY):
        self.stats_time_unit = stats_time_unit
        self.current_section = None
        super(PageviewStats, self).__init__(name, stats_redis, stats_db)

    def stats(self, message):
        """PV stats

        Message's keys:
        "page, timestamp" are required keys, "rid, view" are optional keys.
        """
        page = message["page"]
        timestamp = message["timestamp"]
        rid = message.get("rid", None)
        # optional params
        views = int(message.get("views", 1))
        section = int(timestamp) / self.stats_time_unit

        base_key = "%s:%s" % (self._stats_key_prefix, self.name)

        if rid:
            page_key = "%s-%s" % (page, rid)
        else:
            page_key = page

        pipe = self.redis.pipeline()
        # stats:api:time:2271792, records within time_unit
        time_key = "%s:time:%s" % (base_key, section)
        pipe.zincrby(time_key, page_key, views)
        pipe.expire(time_key, options.stats_time_expire)
        pipe.execute()

        if self.current_section != section:
            self.current_section = section
            self.prepare_to_sync()

    def sync_to_db(self):
        base_key = "%s:%s" % (self._stats_key_prefix, self.name)
        for i in xrange(1, options.stats_db_sync_max_units):
            section = self.current_section - i
            time_key = "%s:time:%s" % (base_key, section)
            count = self.redis.zcard(time_key)
            if count:
                limit = 200
                offset = 0
                while True:
                    logs = self.redis.zrange(time_key, offset,
                                             offset + limit - 1, withscores=True)
                    if logs:
                        self._sync_views_to_db(logs, section)
                        offset += len(logs)
                    else:
                        break

                self.redis.delete(time_key)

            i += 1

    def _sync_views_to_db(self, logs, section):
        viewed_at = section * self.stats_time_unit
        params = []
        for page_key, views in logs:
            v = page_key.split("--")
            if len(v) >= 2:
                rid = v[-1]
            else:
                rid = None
            page = v[0]
            if views > int(options.stats_db_sync_min_views):
                params.append((self.name, page, views, rid, viewed_at))
                logging.debug("sync_views_to_db: %s %s" % (page_key, int(views)))

        self.db.executemany("INSERT into pageview_logs (name, page, views, rid, "
                            "viewed_at) values (%s, %s, %s, %s, FROM_UNIXTIME(%s))",
                            params)
