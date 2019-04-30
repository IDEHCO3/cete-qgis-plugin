
# coding: utf-8

import Utils

from qgis.utils import iface
from qgis.core import QgsDataSourceURI, QgsVectorLayer, QgsMessageLog

from PyQt4.QtSql import *
from PyQt4.QtCore import QThread, QObject, QEventLoop, pyqtSignal

from dialog_base import BaseDialog
#from gui.dialog_base_v2 import BaseDialog
from PostgresCon import PostgresCon
from QueryMemoryLayer import QueryMemoryLayer
import PluginSettings

class BaseDialogController(QObject):
    def __init__(self):
        super(BaseDialogController, self).__init__()
        self.view = BaseDialog()

    def showView(self):
        self.view.show()
        self.view.exec_()

        self.view.getBtShowCete().clicked.connect(self._clickedBtShowCete)
        self.view.getBtShowOsm().clicked.connect(self._clickedBtShowOsm)
        self.view.getBtIntersection().clicked.connect(self._clickedBtIntersection)
        self.view.getBtShowBuffer().clicked.connect(self._clickedBtShowBuffer)
        self.view.getBtCeteMinusIntersection().clicked.connect(self._clickedBtCeteMinusIntersection)
        self.view.getBtOsmMinusIntersection().clicked.connect(self._clickedBtOsmMinusIntersection)
        self.view.getBtCeteQuickDiff().clicked.connect(self._clickedBtCeteQuickDiff)
        self.view.getBtOsmQuickDiff().clicked.connect(self._clickedBtOsmQuickDiff)
        self.view.getBtOsmVerifyNames().clicked.connect(self._clickedOsmVerifyNames)

        self.view.text_geocod.textChanged.connect(self._geocod_changed)

        self.view.setProgressVisible(False)

        self.setup_gui()
       
    def setup_gui(self):
        view = self.view
        config = PluginSettings.get
        
        view.text_host.setText(config('host'))
        view.text_port.setText(config('port'))
        view.text_dbname.setText(config('dbname'))
        view.text_user.setText(config('user'))
        view.text_password.setText(config('password'))

        view.text_osm_table.setText(config('osm_table'))
        view.text_cete_table.setText(config('cete_table'))
        view.text_geocod.setText(config('geocod'))
        view.text_buffer_size.setText(config('buffers_size'))

    def save_settings(self):
        set = PluginSettings.set

        set('host', self.host())
        set('port', self.port())
        set('dbname', self.dbName())
        set('user', self.user())
        set('password', self.password())
        set('cete_table', self.ceteTable())
        set('osm_table', self.osmTable())
        set('geocod', self.geocod())
        set('buffer_size', self.view.bufferSize())

    # Progress Bar
    def progress(self, value, text):
        self.view.get_progress_bar().setValue(value)
        self.view.get_progress_label().setText(text)

    # Prepare a query string and create uri to make a QueryMemoryLayer
    def prepareLayerQuery(self, query, name_layer='layer', geom_type='linestring'):
        str_query = self.prepareStringQuery(query)

        uri = QgsDataSourceURI()
        uri.setConnection(self.host(), self.port(), self.dbName(), self.user(), self.password(), QgsDataSourceURI.SSLdisable)
        uri.setDataSource('', str_query, 'geom', '')
        uri.setKeyColumn('_uid_')
        uri.setParam('geom_type', geom_type)
        
        l = QueryMemoryLayer(uri, name_layer, str_query)
        
        return l

    def geocodList(self):
        import re

        pattern = r'([0-9]+)+'
        match = re.findall(pattern, self.geocod())

        return match

    # Wraps a query into qgis format. Qgis must have the first column with unique value
    def queryWrapper(self, query):
        return u'(SELECT row_number() over() as _uid_,* FROM ( {} ) AS sub_qry1)'.format(query)

    def prepareStringQuery(self, query):
        strQuery = ''.join(query.encode('utf-8').split('\n'))
        strQuery = self.queryWrapper(strQuery)
        
        return strQuery

    def show_progress_box(self, bool_):
        self.view.setProgressVisible(bool_)
        self.view.get_progress_label().setText('Status')

    def block_ui_elements(self, bool_):
        self.view.get_button_box().setEnabled(not bool_)
        self.view.get_table_box().setEnabled(not bool_)

    def block_ui_and_show_progress_bar(self, bool_):
        self.block_ui_elements(bool_)
        self.show_progress_box(bool_)

    def add_layer_on_qgis(self, layer, query):
        Utils.Logging.info(u'Adicionando camada: ' + layer.name(), 'OSMPlugin')

        Utils.Layer.add(layer)

        # Registering layer.executeQuery method as thread Task
        task = Task(layer.executeQuery, query)
        task.start()

        query_result = task.result
        layer.fill(query_result)

        Utils.Logging.info(u'Feições carregadas: ' + layer.name(), 'OSMPlugin')

    # Cria a camada com eixos da CETE
    def _clickedBtShowCete(self):
        self.save_settings()
        self.block_ui_and_show_progress_bar(True)

        for index, geocod in enumerate(self.geocodList()):
            query = self.getCeteEixosQuery(geocod)

            muni = self.nome_municipio(geocod)
            layer_name = u'CETE: {}'.format(muni)
            layer = self.prepareLayerQuery(query, layer_name)

            # Progress bar feedback
            progress = float(index) / float(len(self.geocodList())) * 100
            self.progress(progress, u'Processando: {muni} ({num}/{deno})'.format(muni=muni, num=index,
                                                                                 deno=len(self.geocodList())))

            self.add_layer_on_qgis(layer, query)

        self.block_ui_and_show_progress_bar(False)

    # Cria a camada com roads da OSM
    def _clickedBtShowOsm(self):
        self.save_settings()
        self.block_ui_and_show_progress_bar(True)

        for index, geocod in enumerate(self.geocodList()):
            query = self.getOsmRoadsQuery(geocod)

            muni = self.nome_municipio(geocod)
            layer_name = u'OSM: {}'.format(muni)
            layer = self.prepareLayerQuery(query, layer_name)

            # Progress bar feedback
            progress = float(index) / float(len(self.geocodList())) * 100
            self.progress(progress, u'Processando: {muni} ({num}/{deno})'.format(muni=muni, num=index,
                                                                                 deno=len(self.geocodList())))

            self.add_layer_on_qgis(layer, query)

        self.block_ui_and_show_progress_bar(False)

    #
    def _clickedBtIntersection(self):
        self.save_settings()
        self.block_ui_and_show_progress_bar(True)

        for index, geocod in enumerate(self.geocodList()):
            query = self.getIntersectionQuery(geocod)

            muni = self.nome_municipio(geocod)
            layer_name = u'Intersecao {}m: {}'.format(self.view.bufferSize(), muni)
            layer = self.prepareLayerQuery(query, layer_name)

            # Progress bar feedback
            progress = float(index) / float(len(self.geocodList())) * 100
            self.progress(progress, u'Processando: {muni} ({num}/{deno})'.format(muni=muni, num=index,
                                                                                 deno=len(self.geocodList())))

            self.add_layer_on_qgis(layer, query)

        self.block_ui_and_show_progress_bar(False)

    # Mostra o buffer no mapa da OSM
    def _clickedBtShowBuffer(self):
        self.save_settings()
        self.block_ui_and_show_progress_bar(True)

        for index, geocod in enumerate(self.geocodList()):
            query = self.getBufferOsmQuery(geocod)

            muni = self.nome_municipio(geocod)
            layer_name = u'Buffer{}m: {}'.format(self.view.bufferSize(), muni)
            layer = self.prepareLayerQuery(query, layer_name, 'polygon')

            # Progress bar feedback
            progress = float(index) / float(len(self.geocodList())) * 100
            self.progress(progress, u'Processando: {muni} ({num}/{deno})'.format(muni=muni, num=index,
                                                                                 deno=len(self.geocodList())))

            self.add_layer_on_qgis(layer, query)

        self.block_ui_and_show_progress_bar(False)
        
    def _clickedBtOsmMinusIntersection(self):
        self.save_settings()
        self.block_ui_and_show_progress_bar(True)

        for index, geocod in enumerate(self.geocodList()):
            query = self.getOsmDiffQuery(geocod)

            muni = self.nome_municipio(geocod)
            layer_name = u'OSM diff: {}'.format(muni)
            layer = self.prepareLayerQuery(query, layer_name)

            # Progress bar feedback
            progress = float(index) / float(len(self.geocodList())) * 100
            self.progress(progress, u'Processando: {muni} ({num}/{deno})'.format(muni=muni, num=index,
                                                                                 deno=len(self.geocodList())))

            self.add_layer_on_qgis(layer, query)

        self.block_ui_and_show_progress_bar(False)

    def _clickedBtCeteMinusIntersection(self):
        self.save_settings()
        self.block_ui_and_show_progress_bar(True)

        for index, geocod in enumerate(self.geocodList()):
            query = self.getCeteDiffQuery(geocod)

            muni = self.nome_municipio(geocod)
            layer_name = u'CETE diff: {}'.format(muni)
            layer = self.prepareLayerQuery(query, layer_name)

            # Progress bar feedback
            progress = float(index) / float(len(self.geocodList())) * 100
            self.progress(progress, u'Processando: {muni} ({num}/{deno})'.format(muni=muni, num=index,
                                                                                 deno=len(self.geocodList())))

            self.add_layer_on_qgis(layer, query)

        self.block_ui_and_show_progress_bar(False)

    def _clickedBtCeteQuickDiff(self):
        self.save_settings()
        self.block_ui_and_show_progress_bar(True)

        for index, geocod in enumerate(self.geocodList()):
            query = self.getCeteQuickDiffQuery(geocod)

            muni = self.nome_municipio(geocod)
            layer_name = u'CETE quickdiff: {}'.format(muni)
            layer = self.prepareLayerQuery(query, layer_name)

            # Progress bar feedback
            progress = float(index) / float(len(self.geocodList())) * 100
            self.progress(progress, u'Processando: {muni} ({num}/{deno})'.format(muni=muni, num=index,
                                                                                 deno=len(self.geocodList())))

            self.add_layer_on_qgis(layer, query)

        self.block_ui_and_show_progress_bar(False)

    def _clickedBtOsmQuickDiff(self):
        self.save_settings()
        self.block_ui_and_show_progress_bar(True)

        for index, geocod in enumerate(self.geocodList()):
            query = self.getOsmQuickDiffQuery(geocod)

            muni = self.nome_municipio(geocod)
            layer_name = u'OSM quickdiff: {}'.format(muni)
            layer = self.prepareLayerQuery(query, layer_name)

            # Progress bar feedback
            progress = float(index) / float(len(self.geocodList())) * 100
            self.progress(progress, u'Processando: {muni} ({num}/{deno})'.format(muni=muni, num=index,
                                                                                 deno=len(self.geocodList())))

            self.add_layer_on_qgis(layer, query)

        self.block_ui_and_show_progress_bar(False)

    def _clickedOsmVerifyNames(self, geocod=None):
        self.save_settings()
        self.block_ui_and_show_progress_bar(True)

        for index, geocod in enumerate(self.geocodList()):
            query = self.getOSMExclusiveNameQuery(geocod)

            muni = self.nome_municipio(geocod)
            layer_name = u'OSM Nomes: {}'.format(muni)
            layer = self.prepareLayerQuery(query, layer_name)

            # Progress bar feedback
            progress = float(index) / float(len(self.geocodList())) * 100
            self.progress(progress, u'Processando: {muni} ({num}/{deno})'.format(muni=muni, num=index,
                                                                                 deno=len(self.geocodList())))

            self.add_layer_on_qgis(layer, query)

        self.block_ui_and_show_progress_bar(False)

    def _geocod_changed(self, text):
        name = self.nome_municipio(text) if len(self.geocodList()) <= 1 else '---'

        self.view.label_city.setText(name)

    def nome_municipio(self, geocod=''):
        db = PostgresCon(
            host=self.host(),
            port=int(self.port()),
            dbname=self.dbName(),
            user=self.user(),
            password=self.password()
        )

        query = db.select(u"SELECT nm_municipio FROM t_lm_municipios WHERE cd_geocodigo = {}::text".format(geocod))

        query.first()
        value = query.value(0)

        return value

    def getView(self):
        return self.view

    def host(self):
        return self.view.host()

    def port(self):
        return self.view.port()

    def dbName(self):
        return self.view.dbName()

    def user(self):
        return self.view.user()

    def password(self):
        return self.view.password()

    def osmTable(self):
        return self.view.osmTable()

    def ceteTable(self):
        return self.view.ceteTable()

    def geocod(self):
        return self.view.geocod()

    def bufferSize(self):
        return float(self.view.bufferSize()) / 111000.0

    def getMunicipiosInfo(self):
        get = PluginSettings.get
        return {
            'table_name': get('municipios')['table_name'],
            'geocodigo_field': get('municipios')['geocodigo_field'],
            'geom_field': get('municipios')['geom_field']
        }

    def getOsmRoadsQuery(self, geocod=None):
        query =  u"""
        SELECT 
            roads.gid, 
            roads.name, 
            roads.geom as geom 
        FROM 
            {osm_roads} AS roads, 
            {municipios[table_name]} AS muni 
        WHERE st_contains(muni.{municipios[geom_field]}, roads.geom) 
        AND muni.{municipios[geocodigo_field]}::text = {geocodigo}::text
        """.format(
            osm_roads=self.osmTable(),
            municipios=self.getMunicipiosInfo(),
            geocodigo=geocod or self.geocod()
        )

        return query
    
    def getCeteEixosQuery(self, geocod=None):
        query = u"""
        SELECT 
            roads.id as gid, 
            roads.nm_txtmemo AS name, 
            roads.geom as geom 
        FROM 
            {cete_roads} AS roads, 
            {municipios[table_name]} AS muni 
        WHERE st_contains(muni.{municipios[geom_field]}, roads.geom) 
        AND muni.{municipios[geocodigo_field]}::text = {geocodigo}::text
        """.format(
            cete_roads=self.ceteTable(),
            geocodigo=geocod or self.geocod(),
            municipios=self.getMunicipiosInfo(),
        )

        return query
    
    def getBufferOsmQuery(self, geocod=None):
        query = u"""
        SELECT 
            roads.gid, 
            roads.name, 
            st_buffer(roads.geom, {buffer_size}) AS geom 
        FROM 
            {osm_roads} AS roads, 
            {municipios[table_name]} AS muni 
        WHERE st_contains(muni.{municipios[geom_field]}, roads.geom) 
        AND muni.{municipios[geocodigo_field]}::text = {geocodigo}::text
        """.format(
            osm_roads=self.osmTable(),
            buffer_size=self.bufferSize(),
            municipios=self.getMunicipiosInfo(),
            geocodigo=geocod or self.geocod()
        )

        return query
    
    def getIntersectionQuery(self, geocod=None):
        query = u"""
        WITH 
        params(geocodigo, buffer_size) AS (
            VALUES({geocodigo}::text, {buffer_size}::double precision)
        ),
        muni AS
        (
            SELECT
                {municipios[geocodigo_field]} AS cd_geocodigo, {municipios[geom_field]} AS gm_area
            FROM
                params, {municipios[table_name]}
            WHERE
                {municipios[geocodigo_field]} = params.geocodigo
        ),
        osm_roads AS
        (
            SELECT
                roads.gid,
                roads.name,
                roads.geom
            FROM
                {osm_roads} as roads, muni
            WHERE st_contains(muni.gm_area, roads.geom)
        ),
        cete_roads AS
        (
            SELECT
                roads.gid,
                roads.nm_txtmemo AS name,
                roads.geom
            FROM 
                {cete_roads} AS roads, muni
            WHERE st_contains(muni.gm_area, roads.geom)
        ),
        osm_buffer AS
        (
            SELECT
                osm.gid,
                osm.name,
                st_buffer(osm.geom, params.buffer_size, 4) AS geom
            FROM
                params,
                osm_roads osm
        )
        
        SELECT 
            row_number() over() as id,
            b.cete_gid, b.cete_logradouro::text,
            b.osm_gid, b.osm_logradouro::text,
            b.geom
        FROM
        (
            SELECT DISTINCT ON (cete.gid)
                cete.gid AS cete_gid,
                cete.name AS cete_logradouro,
                osm.gid AS osm_gid,
                osm.name AS osm_logradouro,
                cete.geom AS geom
            FROM
                cete_roads AS cete,
                osm_buffer AS osm
            WHERE
                st_within(cete.geom, osm.geom)
                
            UNION ALL
            
            SELECT
                cete.gid AS cete_gid,
                cete.name AS cete_logradouro,
                osm.gid AS osm_gid,
                osm.name AS osm_logradouro,
                ST_LineMerge(ST_Intersection(cete.geom, osm.geom)) as geom
            FROM
                params,
                cete_roads AS cete,
                osm_buffer AS osm
            WHERE
                st_intersects(cete.geom, osm.geom)
                AND NOT st_within(cete.geom, osm.geom)
                AND ST_Length(ST_intersection(cete.geom, osm.geom)) > 3 * params.buffer_size
        ) AS b
        """.format(
            geocodigo=geocod or self.geocod(),
            buffer_size=self.bufferSize(),
            municipios=self.getMunicipiosInfo(),
            osm_roads=self.osmTable(),
            cete_roads=self.ceteTable()
        )

        return query
        
    def getOsmDiffQuery(self, geocod=None):
        query = u"""
        WITH
        params(geocodigo, buffer_size) AS (VALUES({geocodigo}, {buffer_size})),
        muni AS (
            SELECT {municipios[geocodigo_field]} AS cd_geocodigo, {municipios[geom_field]} AS gm_area
            FROM {municipios[table_name]}, params
            WHERE {municipios[geocodigo_field]} = params.geocodigo::text
        ),
        osm AS (
            SELECT roads.gid, roads.name, roads.geom
            FROM ({osm_roads}) as roads, muni
            WHERE ST_Within(roads.geom, muni.gm_area)
        ),
        inter AS (
            SELECT st_union(st_buffer(i.geom, params.buffer_size::double precision, 4)) AS geom
            FROM params, LATERAL ({intersection_query}) AS i
        ),
        quick_diff AS (
            SELECT osm.gid, osm.name, osm.geom AS geom
            FROM osm, inter
            WHERE NOT ST_Within(osm.geom, inter.geom)
        )
        
        SELECT diff.gid, diff.name AS logradouro, st_difference(diff.geom, inter.geom) AS geom
        FROM quick_diff as diff, inter
        WHERE ST_Intersects(diff.geom, inter.geom)
        
        UNION
        
        SELECT diff.gid, diff.name AS logradouro, diff.geom 
        FROM quick_diff AS diff, inter
        WHERE NOT ST_Intersects(diff.geom, inter.geom)
        """.format(
            geocodigo=geocod or self.geocod(),
            osm_roads=self.getOsmRoadsQuery(geocod),
            buffer_size=self.bufferSize(),
            intersection_query=self.getIntersectionQuery(geocod),
            municipios=self.getMunicipiosInfo()
        )

        return query
    
    def getCeteDiffQuery(self, geocod=None):
        query = u""" 
        WITH
        params(geocodigo, buffer_size) AS (VALUES({geocodigo}, {buffer_size})),
        muni AS (
            SELECT {municipios[geocodigo_field]} AS cd_geocodigo, {municipios[geom_field]} AS gm_area
            FROM {municipios[table_name]}, params
            WHERE {municipios[geocodigo_field]} = params.geocodigo::text
        ),
        cete AS (
            SELECT c.gid AS gid, c.name AS name, c.geom
            FROM ({cete_roads}) AS c, muni
            WHERE ST_Within(c.geom, muni.gm_area)
        ),
        inter AS (
            SELECT st_union(st_buffer(i.geom, params.buffer_size::double precision, 4)) AS geom
            FROM params, LATERAL ({intersection_query}) AS i
        ),
        quick_diff AS (
            SELECT cete.gid, cete.name, cete.geom AS geom
            FROM cete, inter
            WHERE NOT ST_Within(cete.geom, inter.geom)
        )
        
        SELECT diff.gid, diff.name AS logradouro, st_difference(diff.geom, inter.geom) AS geom
        FROM quick_diff AS diff, inter
        WHERE ST_Intersects(diff.geom, inter.geom)
        
        UNION
        
        SELECT diff.gid, diff.name AS logradouro, diff.geom 
        FROM quick_diff AS diff, inter
        WHERE NOT ST_Intersects(diff.geom, inter.geom)
        """.format(
            geocodigo=geocod or self.geocod(),
            cete_roads=self.getCeteEixosQuery(),
            buffer_size=self.bufferSize(),
            intersection_query=self.getIntersectionQuery(),
            municipios=self.getMunicipiosInfo()
        )

        return query
        
    def getOsmQuickDiffQuery(self, geocod=None):
        query = u"""
        SELECT 
            osm.gid, 
            osm.name AS logradouro, 
            osm.geom AS geom 
        FROM 
            ( {osm_roads} ) AS osm, 
            ( 
                SELECT 
                    st_union(st_buffer(_intersection.geom, {buffer_size}::double precision, 4)) AS geom 
                FROM 
                ( 
                    {intersection_query} 
                ) AS _intersection 
            ) _intersec 
        WHERE NOT ST_Within(osm.geom, _intersec.geom)
        """.format(
            osm_roads=self.getOsmRoadsQuery(geocod or self.geocod()),
            buffer_size=self.bufferSize(),
            intersection_query=self.getIntersectionQuery(geocod or self.geocod())
        )

        return query

    def getCeteQuickDiffQuery(self, geocod=None):
        return u"""
        SELECT 
            qf.gid, 
            qf.name AS logradouro, 
            qf.geom AS geom 
        FROM 
            ( {cete_roads} ) AS qf, 
            ( 
                SELECT 
                    st_union(st_buffer(_intersection.geom, {buffer_size}::double precision, 4)) AS geom 
                FROM 
                ( {intersection_query} ) AS _intersection 
            ) AS _intersec 
        WHERE NOT ST_Within(qf.geom, _intersec.geom)
        """.format(
            cete_roads=self.getCeteEixosQuery(geocod or self.geocod()),
            buffer_size=self.bufferSize(),
            intersection_query=self.getIntersectionQuery(geocod or self.geocod())
        )

    def getOSMExclusiveNameQuery(self, geocod=None):
        query = u"""
            SELECT * 
            FROM 
                ( {intersection_query} ) as i
            WHERE
                (cete_logradouro is null or cete_logradouro = 'RUA SEM NOME' or cete_logradouro = 'SEM NOME') and osm_logradouro is not null
            """.format(
                intersection_query=self.getIntersectionQuery(geocod)
            )

        return query

class Task(QObject):
    started = pyqtSignal()
    finished = pyqtSignal()

    def __init__(self, callback, *args, **kwargs):
        super(Task, self).__init__()

        self._callback = callback
        self._args = args
        self._kwargs = kwargs
        self.result = None

        self.thread = QThread(iface.mainWindow())
        self.thread.run = self.run
        self.thread.finished.connect(self.exit_loop)

        self.loop = QEventLoop()

    def run(self):
        self.result = self._callback(*self._args, **self._kwargs)

    def start(self):
        self.started.emit()
        self.moveToThread(self.thread)
        self.thread.start()

        self.loop.exec_()

    def exit_loop(self):
        self.loop.exit()
        self.finished.emit(self.result)
