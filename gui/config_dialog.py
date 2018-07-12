# -*- coding: utf-8 -*-
"""
/***************************************************************************

                                 QgisLocator

                             -------------------
        begin                : 2018-05-03
        copyright            : (C) 2018 by Denis Rouzaud
        email                : denis@opengis.ch
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import QDialog, QTableWidgetItem, QAbstractItemView, QComboBox
from qgis.PyQt.uic import loadUiType
from qgis.core import QgsLocatorFilter

from ..qgissettingmanager.setting_dialog import SettingDialog, UpdateMode
from ..core.settings import Settings

DialogUi, _ = loadUiType(os.path.join(os.path.dirname(__file__), '../ui/config.ui'))


class ConfigDialog(QDialog, DialogUi, SettingDialog):
    def __init__(self, parent=None):
        settings = Settings()
        QDialog.__init__(self, parent)
        SettingDialog.__init__(self, setting_manager=settings, mode=UpdateMode.DialogAccept)
        self.setupUi(self)

        # try:
        cb = self.findChild(QComboBox, 'locations_priority')
        cb.addItem(self.tr('Highest'), QgsLocatorFilter.Highest)
        cb.addItem(self.tr('High'), QgsLocatorFilter.High)
        cb.addItem(self.tr('Medium'), QgsLocatorFilter.Medium)
        cb.addItem(self.tr('Low'), QgsLocatorFilter.Low)
        cb.addItem(self.tr('Lowest'), QgsLocatorFilter.Lowest)
        for cb_name in ['location_default', 'location_housenumber']:
            cb = self.findChild(QComboBox, '{}_zoom'.format(cb_name))
            cb.addItem('1:1000','1000')
            cb.addItem('1:2000','2000')
            cb.addItem('1:5000','5000')
            cb.addItem('1:10000','10000')
            cb.addItem('1:25000','25000')
        # except Exception as e:
        #     pass

        self.settings = settings
        self.init_widgets()