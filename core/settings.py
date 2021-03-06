# -*- coding: utf-8 -*-
# -----------------------------------------------------------
#
# QGIS Swiss Locator Plugin
# Copyright (C) 2018 Denis Rouzaud
#
# -----------------------------------------------------------
#
# licensed under the terms of GNU GPL 2
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# ---------------------------------------------------------------------


from qgis.core import QgsLocatorFilter
from ..qgissettingmanager import *

pluginName = "ban_locator_plugin"


class Settings(SettingManager):
    def __init__(self):
        SettingManager.__init__(self, pluginName)

        self.add_setting(Enum('locations_priority', Scope.Global, QgsLocatorFilter.Highest))
        self.add_setting(Integer('locations_limit', Scope.Global, 10))
        
        self.add_setting(String('location_default_zoom', Scope.Global, '25000'))
        self.add_setting(String('location_housenumber_zoom', Scope.Global, '2000'))
        self.add_setting(Bool('keep_marker_visible', Scope.Global, True))

