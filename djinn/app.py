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

"""Base Application"""

import os

from tornado.locale import load_translations
from tornado.web import Application


class DjinnApplication(Application):

    """Base Application for djinn framework"""

    def reverse_api(self, request):
        """Returns a URL name for a request"""
        handlers = self._get_host_handlers(request)

        for spec in handlers:
            match = spec.regex.match(request.path)
            if match:
                return spec.name

        return None

translation_folder = "translations"
here = os.path.dirname(os.path.realpath(__file__))
load_translations(os.path.join(here, translation_folder))

app_translation = os.path.join(os.getcwd(), translation_folder)
if os.path.isdir(app_translation):
    load_translations(app_translation)
