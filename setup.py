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

import distutils.core
try:
    import setuptools
except ImportError:
    pass

version = "1.1.1"

distutils.core.setup(
    name="djinn",
    version=version,
    packages=["djinn", "djinn.datastore", "djinn.stats"],
    package_dir={'djinn': 'djinn'},
    package_data={'djinn': ['translations/*.csv']},
    author="Felinx Lee",
    author_email="felinx.lee@gmail.com",
    url="https://github.com/felinx/djinn",
    license="http://www.apache.org/licenses/LICENSE-2.0",
    description="Djinn is a micro-framework which wraps Tornado to make it easy to write a web application using Tornado.",
)
