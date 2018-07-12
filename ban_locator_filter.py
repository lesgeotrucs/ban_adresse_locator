# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Date : July 2018
 Author : Geotrucs
 Based on
 QGIS Swiss Locator Plugin
 Copyright (C) 2018 Denis Rouzaud

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


import json
import os
import re
import sys, traceback
from enum import Enum

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import QLabel, QWidget
from PyQt5.QtCore import QUrl, QUrlQuery, pyqtSignal, QEventLoop

from qgis.core import Qgis, QgsLocatorFilter, QgsLocatorResult, QgsRectangle, QgsApplication, \
    QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject, QgsGeometry, QgsWkbTypes, QgsPointXY, \
    QgsLocatorContext, QgsFeedback, QgsRasterLayer
from qgis.gui import QgsRubberBand, QgisInterface

from .core.network_access_manager import NetworkAccessManager, RequestsException, RequestsExceptionUserAbort
from .core.settings import Settings
from .gui.config_dialog import ConfigDialog
from .ban_locator_plugin import DEBUG

import time

#type de résultat trouvé
TYPE_RESULT = {'housenumber': 'Numéro à la plaque',
               'street' : 'Voie',
               'locality' : 'Lieu-dit',
               'municipality' : 'Commune'}

class NoResult:
    pass

class InvalidBox(Exception):
    pass

class LocationResult:
    def __init__(self, importance, citycode, score, type_result, label, x, y):
        self.importance = importance
        self.citycode = citycode
        self.score = score
        self.type_result = type_result
        self.label = label
        self.point = QgsPointXY(x,y)



class BanLocatorFilter(QgsLocatorFilter):

    HEADERS = {b'User-Agent': b'Mozilla/5.0 QGIS BAN Locator Filter'}

    message_emitted = pyqtSignal(str, str, Qgis.MessageLevel, QWidget)

    def __init__(self, iface: QgisInterface = None):
        """"
        :param filter_type: the type of filter
        :param locale_lang: the language of the locale.
        :param iface: QGIS interface, given when on the main thread (which will display/trigger results), None otherwise
        :param crs: if iface is not given, it shall be provided, see clone()
        """
        super().__init__()
        self.rubber_band = None
        self.feature_rubber_band = None
        self.iface = iface
        self.map_canvas = None
        self.settings = Settings()
        self.transform_4326 = None
        self.current_timer = None
        self.crs = None
        self.event_loop = None
        self.result_found = False
        self.search_delay = 0.5
        self.dbg_info("initialisation")


        if iface is not None:
            # happens only in main thread
            self.map_canvas = iface.mapCanvas()
            self.map_canvas.destinationCrsChanged.connect(self.create_transforms)

            self.rubber_band = QgsRubberBand(self.map_canvas, QgsWkbTypes.PointGeometry)
            self.rubber_band.setColor(QColor(255, 255, 50, 200))
            self.rubber_band.setIcon(self.rubber_band.ICON_CIRCLE)
            self.rubber_band.setIconSize(15)
            self.rubber_band.setWidth(4)
            self.rubber_band.setBrushStyle(Qt.NoBrush)

            self.feature_rubber_band = QgsRubberBand(self.map_canvas, QgsWkbTypes.PolygonGeometry)
            self.feature_rubber_band.setColor(QColor(255, 50, 50, 200))
            self.feature_rubber_band.setFillColor(QColor(255, 255, 50, 160))
            self.feature_rubber_band.setBrushStyle(Qt.SolidPattern)
            self.feature_rubber_band.setLineStyle(Qt.SolidLine)
            self.feature_rubber_band.setWidth(4)

            self.create_transforms()

    def name(self):
        return 'Recherche Adresse BAN'

    def clone(self):
        return BanLocatorFilter(self.iface)

    def priority(self):
        return self.settings.value('locations_priority')

    def displayName(self):
        return self.tr('Ban Adress Location')

    def prefix(self):
        return 'ban'

    def clearPreviousResults(self):
        self.rubber_band.reset(QgsWkbTypes.PointGeometry)
        self.feature_rubber_band.reset(QgsWkbTypes.PolygonGeometry)

        if self.current_timer is not None:
            self.current_timer.stop()
            self.current_timer.deleteLater()
            self.current_timer = None

    def hasConfigWidget(self):
        return True

    def openConfigWidget(self, parent=None):
        ConfigDialog(parent).exec_()

    def create_transforms(self):
        # this should happen in the main thread
        dst_crs = self.map_canvas.mapSettings().destinationCrs()
        src_crs_4326 = QgsCoordinateReferenceSystem('EPSG:4326')
        self.transform_4326 = QgsCoordinateTransform(src_crs_4326, dst_crs, QgsProject.instance())

    def group_info(self, group: str) -> str:
        return TYPE_RESULT[group]

    @staticmethod
    def url_with_param(url, params) -> str:
        url = QUrl(url)
        q = QUrlQuery(url)
        for key, value in params.items():
            q.addQueryItem(key, value)
        url.setQuery(q)
        return url.url()

    def fetchResults(self, search: str, context: QgsLocatorContext, feedback: QgsFeedback):
        try:
            self.dbg_info("start Ban locator search...")

            if len(search) < 5:
                return

            self.result_found = False

            url = 'https://api-adresse.data.gouv.fr/search/'
            params = {
                'q': str(search),
                'limit': str(self.settings.value('locations_limit'))
            }

            # Locations, WMS layers
            nam = NetworkAccessManager()
            feedback.canceled.connect(nam.abort)
            url = self.url_with_param(url, params)
            self.dbg_info(url)
            try:
                (response, content) = nam.request(url, headers=self.HEADERS, blocking=True)
                self.handle_response(response)
            except RequestsExceptionUserAbort:
                pass
            except RequestsException as err:
                self.info(err)

            if not self.result_found:
                result = QgsLocatorResult()
                result.filter = self
                result.displayString = self.tr('No result found.')
                result.userData = NoResult
                self.resultFetched.emit(result)

        except Exception as e:
            self.info(e, Qgis.Critical)
            exc_type, exc_obj, exc_traceback = sys.exc_info()
            filename = os.path.split(exc_traceback.tb_frame.f_code.co_filename)[1]
            self.info('{} {} {}'.format(exc_type, filename, exc_traceback.tb_lineno), Qgis.Critical)
            self.info(traceback.print_exception(exc_type, exc_obj, exc_traceback), Qgis.Critical)

    def handle_response(self, response):
        try:
            if response.status_code != 200:
                if not isinstance(response.exception, RequestsExceptionUserAbort):
                    self.info("Error in main response with status code: {} from {}"
                              .format(response.status_code, response.url))
                return

            data = json.loads(response.content.decode('utf-8'))
            # self.dbg_info(data)
            for loc in data['features']:
                importance = loc['properties']['importance']
                citycode = loc['properties']['citycode']
                score = loc['properties']['score']
                type_result = loc['properties']['type']
                label = loc['properties']['label']
                x = float(loc['geometry']['coordinates'][0])
                y = float(loc['geometry']['coordinates'][1])
                result = QgsLocatorResult()
                result.filter = self
                result.displayString = label
                result.group = self.group_info(type_result)
                result.icon = QIcon(":/plugins/swiss_locator/icons/ban_locator.png")
                result.userData = LocationResult(importance, 
                                                 citycode, 
                                                 score, 
                                                 type_result, 
                                                 label, 
                                                 x, 
                                                 y)
                self.result_found = True
                self.resultFetched.emit(result)

        except Exception as e:
            self.info(str(e), Qgis.Critical)
            exc_type, exc_obj, exc_traceback = sys.exc_info()
            filename = os.path.split(exc_traceback.tb_frame.f_code.co_filename)[1]
            self.info('{} {} {}'.format(exc_type, filename, exc_traceback.tb_lineno), Qgis.Critical)
            self.info(traceback.print_exception(exc_type, exc_obj, exc_traceback), Qgis.Critical)

    def triggerResult(self, result: QgsLocatorResult):
        # this should be run in the main thread, i.e. mapCanvas should not be None
        
        # remove any map tip
        self.clearPreviousResults()
            
        if type(result.userData) == NoResult:
            pass
        else:
            point = QgsGeometry.fromPointXY(result.userData.point)
            if not point:
                return

            point.transform(self.transform_4326)

            self.highlight(point, result.userData.type_result)

            if not self.settings.value('keep_marker_visible'):
                self.current_timer = QTimer()
                self.current_timer.timeout.connect(self.clearPreviousResults)
                self.current_timer.setSingleShot(True)
                self.current_timer.start(8000)
                
    def highlight(self, point, type_result=None):

        self.rubber_band.reset(QgsWkbTypes.PointGeometry)
        self.rubber_band.addGeometry(point, None)

        if type_result in ('housenumber', 'street'):
            zoom = float(self.settings.value('location_housenumber_zoom'))
        else:
            zoom = float(self.settings.value('location_default_zoom')) 
        self.map_canvas.setCenter(point.asPoint())
        self.map_canvas.zoomScale(zoom)

    
    def info(self, msg="", level=Qgis.Info, emit_message: bool = False):
        self.logMessage(str(msg), level)
        if emit_message:
            self.message_emitted.emit(msg, level)

    def dbg_info(self, msg=""):
        if DEBUG:
            self.info(msg)