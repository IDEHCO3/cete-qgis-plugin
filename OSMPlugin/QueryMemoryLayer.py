# coding: utf-8

from __future__ import with_statement

from qgis.core import *

from PyQt4.QtCore import *
from PyQt4.QtSql import *

from PostgresCon import PostgresCon
from Utils import Utils
import WkbConverter


class QueryMemoryLayer(QgsVectorLayer):
    fill_complete = pyqtSignal()

    def __init__(self, uri, layer_name, query):
        super(QgsVectorLayer, self).__init__('{}?crs=epsg:4674&index=yes'.format(uri.param('geom_type')), layer_name, 'memory')

        self.uri = uri
        self.query = query

        self.db = PostgresCon(
            host=uri.host(),
            port=int(uri.port()),
            dbname=uri.database(),
            user=uri.username(),
            password=uri.password())

    def __enter__(self):
        self.startEditing()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.updateExtents()
        self.commitChanges()
        self.reload()
        Utils.refreshCanvas()

    def fill(self, result):
        self._createAttributes(result)
        self.fill_complete.emit()

    def append(self, result):
        self.startEditing()

        record = result.record()
        fields = QgsFields()

        for i in range(record.count()):
            if record.fieldName(i) == 'geom':
                continue

            field_name = record.field(i).name()
            field_type = record.field(i).type()

            field = QgsField(field_name, field_type)
            self.addAttribute(field)
            fields.append(field)

        self.updateFields()

        while result.next():
            feature = QgsFeature(fields)

            geom_index = -1
            for i in range(record.count()):
                if record.fieldName(i) == 'geom':
                    geom_index = i
                    continue

                feature.setAttribute(i, result.value(i))

            #wkb = WkbConverter.hexToWkb(result.value(geom_index))

            geom_str = str( result.value(geom_index) )

            g = QgsGeometry()
            g.fromWkb(geom_str)

            feature.setGeometry(g)
            self.addFeature(feature, False)

        self.updateExtents()
        self.commitChanges()
        self.reload()
        Utils.refreshCanvas()

    def executeQuery(self, query):
        result = self.db.select(query)
        return result

    def _createAttributes(self, result):
        record = result.record()
        fields = QgsFields()

        for i in range(record.count()):
            if record.fieldName(i) == 'geom':
                continue

            field_name = record.field(i).name()
            field_type = record.field(i).type()

            field = QgsField(field_name, field_type)
            self.addAttribute(field)
            fields.append(field)

        self.updateFields()

        while result.next():
            feature = QgsFeature(fields)

            i = 0
            geom_index = -1
            for i in range(record.count()):
                if record.fieldName(i) == 'geom':
                    geom_index = i
                    continue

                feature.setAttribute(i, result.value(i))

            wkb = result.value(geom_index)
            #wkb = WkbConverter.hexToWkb(result.value(geom_index))

            g = QgsGeometry()
            g.fromWkb(wkb)

            feature.setGeometry(g)
            self.addFeature(feature, False)

    def force_convert_to_binary(self, geom):
        query = "select ST_AsBinary('{}'::geometry)".format(geom)

        result = self.db.select(query)
        result.next()
        return result.value(0)
