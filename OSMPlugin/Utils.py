
# coding: utf-8

from __future__ import with_statement

from qgis.core import *
from qgis.utils import iface
from qgis.gui import QgsMessageBar

from PyQt4 import QtGui

from .PostgresCon import PostgresCon


class Utils:
    @staticmethod
    # Add a layer
    # @param layer: object type qgis.core.QgsMapLayer
    # @return: None if is no possible add the layer, layer instance otherwise
    def addLayer(layer):
        if layer is None:
            Utils.infoMessage("Layer is null.")
            return None

        l = QgsMapLayerRegistry.instance().addMapLayer(layer)

        if l is None:
            Utils.infoMessage("Impossible to add layer.", 5)
            return None

        return l

    # Get a list of layers with designated name
    # @param name: name of layer
    # @return: List of layers with that name
    @staticmethod
    def getLayersByName(name):
        return QgsMapLayerRegistry.instance().mapLayersByName(name)

    @staticmethod
    def registerLayerType(layer_type):
        return QgsPluginLayerRegistry.instance().addPluginLayerType(layer_type)

    @staticmethod
    # Refresh QGis canvas
    def refreshCanvas():
        iface.mapCanvas().refresh()

    @staticmethod
    def infoMessage(message, duration=3):
        iface.messageBar().pushMessage('Info: ', message, QgsMessageBar.INFO, duration)

    @staticmethod
    def log(msg, tab=None, level=None):
        # level recebe o valor default aqui porque na declaração do método, a classe Logging não era reconhecida
        level = Logging.INFO if not level else level
        QgsMessageLog.instance().logMessage(msg, tab, level)

    @staticmethod
    def message_box(message, title, box_type=None):
        # box_type recebe o valor default aqui porque na declaração do método, a classe MessageBox não era reconhecida
        box_type = MessageBox.INFORMATION if not box_type else box_type
        mes_box = QtGui.QMessageBox(box_type, title, message)
        mes_box.show()
        mes_box.exec_()


class Layer:
    @staticmethod
    def add(layer):
        return Utils.addLayer(layer)

    @staticmethod
    def register_type(layer_type):
        return Utils.registerLayerType(layer_type)

    @staticmethod
    def search_by_name(name):
        return Utils.getLayersByName(name)


class Logging:
    INFO = 0
    WARNING = 1
    CRITICAL = 2

    @staticmethod
    def info(msg, tab=None):
        Utils.log(msg, tab)

    @staticmethod
    def warning(msg, tab=None):
        Utils.log(msg, tab, Logging.WARNING)

    @staticmethod
    def critical(msg, tab=None):
        Utils.log(msg, tab, Logging.CRITICAL)


class MessageBox:
    NO_ICON = 0
    INFORMATION = 1
    WARNING = 2
    CRITICAL = 3
    QUESTION = 4

    @staticmethod
    def info(message, title):
        Utils.message_box(message, title, MessageBox.INFORMATION)

    @staticmethod
    def critical(message, title):
        Utils.message_box(message, title, MessageBox.CRITICAL)

    @staticmethod
    def question(message, title):
        Utils.message_box(message, title, MessageBox.QUESTION)

    @staticmethod
    def warning(message, title):
        Utils.message_box(message, title, MessageBox.WARNING)


class Config:
    @staticmethod
    def has(key):
        import json, os

        path = os.path.dirname(__file__) + '\config.json'

        with open(path, 'r') as file_:
            data = json.loads(file_.read())

        return key in data

    @staticmethod
    def get(key=None):
        import json, os

        path = os.path.dirname(__file__) + '\config.json'

        with open(path, 'r') as file_:
            data = json.loads(file_.read())

        if key:
            if key in data:
                return data[key]

        else:
            return data

    @staticmethod
    def set(key, value):
        import json, os

        path = os.path.dirname(__file__) + '\config.json'

        with open(path, 'r') as file_:
            json_str = file_.read()

            data = {}
            if json_str:
                data = json.loads(json_str)

            data.update({
                key: value
            })

        with open(path, 'w') as file_:
            json.dump(data, file_, indent=2, ensure_ascii=True)

"""
class Database:
    def create_connection(self, name=''):
        switch = {
            'postgres': PostgresCon()
        }

        return switch.get(name)
"""
#========================================================================================================
"""
    @staticmethod
    # @param point: point position from where to search
    # @param pointLayer: layer to search
    # @return: the point closest to 'point' in 'pointLayer'
    def findClosestPoint(point, pointsLayer):

        spIndex = QgsSpatialIndex(pointsLayer.getFeatures())

        nearestIds = spIndex.nearestNeighbor(point.geometry().asPoint(), 1)

        if len(nearestIds) > 0:
            featureId = nearestIds[0]
            fit2 = pointsLayer.getFeatures(QgsFeatureRequest().setFilterFid(featureId))

            return fit2.next()

        return None

    @staticmethod
    # Creates a layer with all extreme vertices marked from a line layer
    # @return: output map layer
    def createExtremeVerticesLayer(nameLayer, outputLayerName='extremeVertices'):
        line_layer = Utils.getLayersByName(nameLayer)

        if len(line_layer) <= 0:
            Utils.infoMessage('No layer founded')
            return None
        else:
            line_layer = line_layer[0]

        point_layer = QgsVectorLayer('Point?crs=epsg:4326&field=gid:long', outputLayerName, 'memory')
        pr = point_layer.dataProvider()
        #pr.addAttributes( [ QgsField('gid', QVariant.LongLong) ] )
        point_layer.updateFields()

        for feature in line_layer.getFeatures():
            geom = feature.geometry().asMultiPolyline()[0]

            if len(geom) <= 0: continue

            fields_model = QgsFields()
            fields_model.append( QgsField('gid', QVariant.LongLong) )

            start_point = QgsPoint(geom[0])
            feat_start = QgsFeature()
            feat_start.setFields(fields_model)
            feat_start['gid'] = feature.attributes()[0]
            feat_start.setGeometry(QgsGeometry.fromPoint(start_point))

            end_point = QgsPoint(geom[-1])
            feat_end = QgsFeature()
            feat_end.setFields(fields_model)
            feat_end['gid'] = feature.attributes()[0]
            feat_end.setGeometry(QgsGeometry.fromPoint(end_point))

            pr.addFeatures([feat_start, feat_end])

        return QgsMapLayerRegistry.instance().addMapLayer(point_layer)


    @staticmethod
    # @param layerName: nome da layer a ser analisada
    # @return: uma layer com pontos em todos os vertices da camada de input
    def createAllVerticesLayer(layerName):

        layer = Utils.getLayersByName(layerName)
        if len(layer) <= 0:
            Utils.infoMessage('No layer with this name {}'.format(layerName))
            return
        else:
            layer = layer[0]

        pointLayer = QgsVectorLayer('Point?crs=epsg:4326&field=gid:long&field=index:integer', 'allVertices', 'memory')
        pr = pointLayer.dataProvider()
        pointLayer.updateFields()

        fields_model = QgsFields()
        fields_model.append( QgsField('gid', QVariant.LongLong) )
        fields_model.append( QgsField('index', QVariant.Int) )

        for feature in layer.getFeatures():
            geom = feature.geometry().asMultiPolyline()
            if len(geom) <= 0: continue

            for line in geom:
                for vertexIndex in range(0, len(line)):
                    feat = QgsFeature()
                    feat.setFields(fields_model)
                    feat['gid'] = feature.attributes()[0]
                    feat['index'] = vertexIndex
                    feat.setGeometry(QgsGeometry.fromPoint(line[vertexIndex]))
                    pr.addFeatures([feat])

        return QgsMapLayerRegistry.instance().addMapLayer(pointLayer)

    @staticmethod
    # Esse processo de correcao procura por pontos mais proximos e tenta aproximar os vertices na camada a ser corrigida
    # @param layerToCorrectName: Nome da layer a ser corrigida
    # @param crossingsLayer: Layer com pontos de cruzamento da camada 'layerToCorrectName'
    # @param pointBaseLayerName: Nome da layer comtendo os pontos de intersecao da camada base
    # @param minPointDistance: a maxima distancia espacial para busca de pontos mais proximos
    # @return: a layer corrigida
    def correction(layerToCorrectName, crossingsLayerName, pointBaseLayerName, maxPointDistance = 0.00025):

        layerToCorrect = Utils.getLayersByName(layerToCorrectName)
        layerToCorrect = layerToCorrect[0] if len(layerToCorrect) > 0 else None
        if layerToCorrect is None:
            infoMessage('No layer with this name: '.format(layerToCorrectName))
            return

        baseLayer = Utils.getLayersByName(pointBaseLayerName)
        baseLayer = baseLayer[0] if len(baseLayer) > 0 else None
        if baseLayer is None:
            infoMessage('No layer with this name: '.format(pointBaseLayerName))
            return

        #vertices_points_layer = Utils.createOutmostVerticesLayer(layerToCorrectName, 'extremeVertices_{}'.format(layerToCorrectName))
        crossingsLayer = Utils.getLayersByName(crossingsLayerName)
        crossingsLayer = crossingsLayer[0] if len(crossingsLayer) > 0 else None
        if crossingsLayer is None:
            infoMessage('No layer with this name: '.format(crossingsLayerName))
            return

        for point in crossingsLayer.getFeatures():

            closest_point = Utils.findClosestPoint(point, baseLayer)
            closest_point = closest_point.geometry().asPoint()

            if closest_point is None:
                continue

            distance = QgsDistanceArea()
            if distance.measureLine(point.geometry().asPoint(), closest_point) > maxPointDistance:
                continue

            # mover o vertice de 'layerToCorrect' para interceptar esse closest_point
            expr = QgsExpression( 'gid={}'.format(point['gid']) )
            feat = layerToCorrect.getFeatures( QgsFeatureRequest( expr ) ).next()

            #Acha indice do vertice
            layerToCorrect.startEditing()
            vertexIndex = 0
            for vertex in feat.geometry().asMultiPolyline()[0]:
                if point.geometry().asPoint().x() == vertex.x() and point.geometry().asPoint().y() == vertex.y():
                    break
                vertexIndex += 1

            layerToCorrect.moveVertex(closest_point.x(), closest_point.y(), feat.id(), vertexIndex)

        Utils.refreshCanvas()
"""
