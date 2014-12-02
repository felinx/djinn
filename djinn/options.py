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

"""tornado.options enhancement"""

import traceback
import os

from tornado.options import parse_command_line, options, define


def parse_config_file(filename):
    """Rewrite tornado default parse_config_file.

    Parses and loads the Python config file at the given filename.
    This version allow customize new options which are not defined before
    from a configuration file.
    """
    config = {}
    execfile(filename, config, config)
    for name in config:
        if name in options._options:
            options._options[name].set(config[name])
        else:
            define(name, config[name])


def parse_options(root_dir, settings_file="settings", parse_cmd=True):
    """Parse options file and command line"""
    try:
        parse_config_file(os.path.join(root_dir, "%s.py" % settings_file))
        # print "Using settings.py as default settings."
    except Exception, exc:
        print "No any default settings, are you sure? Exception: %s" % exc

    try:
        parse_config_file(
            os.path.join(root_dir, "%s_local.py" % settings_file))
        # print "Override some settings with local settings."
    except Exception, exc:
        print "No local settings. Exception: %s" % exc
        # print traceback.format_exc()

    if parse_cmd:
        parse_command_line()
