
# coding: utf-8

"""
/***************************************************************************
 OSMPluginDialog
								 A QGIS plugin
 Extrai interseção e diferenças geométricas e nominais
							 -------------------
		begin				 : 2018-06-05
		git sha				 : $Format:%H$
		copyright			 : (C) 2018 by IBGE
		email				 : andre.censitario@ibge.gov.br
 ***************************************************************************/

/***************************************************************************
 *																		   *
 *	 This program is free software; you can redistribute it and/or modify  *
 *	 it under the terms of the GNU General Public License as published by  *
 *	 the Free Software Foundation; either version 2 of the License, or	   *
 *	 (at your option) any later version.								   *
 *																		   *
 ***************************************************************************/
"""

import os

from OSMPlugin.PostgresCon import PostgresCon

from PyQt4 import QtCore, QtGui, uic
from PyQt4.QtCore import QThread, QObject, QEventLoop, pyqtSignal, Qt
from PyQt4.QtSql import QSql

from OSMPlugin import Utils
from OSMPlugin.gui import dialog_db_info
from OSMPlugin.gui import dialog_geocods
from OSMPlugin.Task import Task
from OSMPlugin.QueryMemoryLayer import QueryMemoryLayer

from qgis.core import QgsDataSourceURI, QgsVectorLayer, QgsVectorFileWriter


class BaseDialogController(QObject):
    database_connected = pyqtSignal()

    def __init__(self):
        super(BaseDialogController, self).__init__()

        self.ui = BaseDialog()
        self.ui_db_connection = dialog_db_info.BaseDialog()
        self.ui_geocods = dialog_geocods.BaseDialog()

        self.db_connection = None
        self.is_db_connection_ok = False

        self.connection_info = Utils.Config.get('connection_info') or {
            "host": "",
            "password": "",
            "user": "",
            "dbname": "",
            "port": 0}
        self.municipios_info = Utils.Config.get('municipios_info') or {
            "geocodigo_field": "",
            "name_field": "",
            "table_name": "",
            "geom_field": ""}
        self.cete_info = Utils.Config.get('cete_info') or {
            "name_field": "",
            "table_name": "",
            "id_field": "",
            "geom_field": ""}
        self.osm_info = Utils.Config.get('osm_info') or {
            "name_field": "",
            "table_name": "",
            "id_field": "",
            "geom_field": ""}
        self.config_info = Utils.Config.get('config_info') or {
            'buffer_size':15,
            'only_one_layer':False,
            'save_in_folder': False,
            'output_folder': ''
        }

        self.ui.bt_database_connection.clicked.connect(self._command_show_db_info)
        self.ui.bt_table_add.clicked.connect(self._command_show_geocods_dialog)
        self.ui_db_connection.accepted.connect(self._command_connect_db)
        self.ui_geocods.accepted.connect(self._command_add_geocods)

        # Assign on dict config
        # Existem dois tipos de sinais de 'currentIndexChanged' em combo boxes. O tipo default do PyQt
        # é o que retorna o índice da combobox, porém aqui eu quero aquele que retorna o texto da combobox,
        # por isso é usado o método connect 'puro'
        QObject.connect(self.ui.cb_table_name_municipio, QtCore.SIGNAL('currentIndexChanged (const QString&)'),
                            lambda value: self._assign(self.municipios_info, 'table_name', value))
        QObject.connect(self.ui.cb_field_name_municipio, QtCore.SIGNAL('currentIndexChanged (const QString&)'),
                            lambda value: self._assign(self.municipios_info, 'name_field', value))
        QObject.connect(self.ui.cb_field_geocod_municipio, QtCore.SIGNAL('currentIndexChanged (const QString&)'),
                            lambda value: self._assign(self.municipios_info, 'geocodigo_field', value))
        QObject.connect(self.ui.cb_field_geom_municipio, QtCore.SIGNAL('currentIndexChanged (const QString&)'),
                            lambda value: self._assign(self.municipios_info, 'geom_field', value))

        QObject.connect(self.ui.cb_table_name_cete, QtCore.SIGNAL('currentIndexChanged (const QString&)'),
                            lambda value: self._assign(self.cete_info, 'table_name', value))
        QObject.connect(self.ui.cb_field_id_cete, QtCore.SIGNAL('currentIndexChanged (const QString&)'),
                            lambda value: self._assign(self.cete_info, 'id_field', value))
        QObject.connect(self.ui.cb_field_name_cete, QtCore.SIGNAL('currentIndexChanged (const QString&)'),
                            lambda value: self._assign(self.cete_info, 'name_field', value))
        QObject.connect(self.ui.cb_field_geom_cete, QtCore.SIGNAL('currentIndexChanged (const QString&)'),
                            lambda value: self._assign(self.cete_info, 'geom_field', value))

        QObject.connect(self.ui.cb_table_name_osm, QtCore.SIGNAL('currentIndexChanged (const QString&)'),
                            lambda value: self._assign(self.osm_info, 'table_name', value))
        QObject.connect(self.ui.cb_field_id_osm, QtCore.SIGNAL('currentIndexChanged (const QString&)'),
                            lambda value: self._assign(self.osm_info, 'id_field', value))
        QObject.connect(self.ui.cb_field_name_osm, QtCore.SIGNAL('currentIndexChanged (const QString&)'),
                            lambda value: self._assign(self.osm_info, 'name_field', value))
        QObject.connect(self.ui.cb_field_geom_osm, QtCore.SIGNAL('currentIndexChanged (const QString&)'),
                            lambda value: self._assign(self.osm_info, 'geom_field', value))

        self.ui.cb_table_name_municipio.editTextChanged.connect(self.check_block_operation_buttons)
        self.ui.cb_field_name_municipio.editTextChanged.connect(self.check_block_operation_buttons)
        self.ui.cb_field_geocod_municipio.editTextChanged.connect(self.check_block_operation_buttons)
        self.ui.cb_field_geom_municipio.editTextChanged.connect(self.check_block_operation_buttons)

        self.ui.bt_table_remove.clicked.connect(self.ui.delete_from_table)
        self.ui.bt_table_select_all.clicked.connect(self.ui.select_all_table)
        self.ui.bt_table_deselect_all.clicked.connect(self.ui.deselect_all_table)

        self.ui.txt_buffer_size.valueChanged.connect(lambda value: self._assign(self.config_info, 'buffer_size', value))
        self.ui.check_all_one_layer.stateChanged.connect(lambda value: self._assign(self.config_info, 'only_one_layer', False if value == Qt.Unchecked else True))
        self.ui.check_save_folder.stateChanged.connect(lambda value: self._assign(self.config_info, 'save_in_folder', False if value == Qt.Unchecked else True))
        self.ui.check_save_folder.stateChanged.connect(self.block_choose_folder_button)

        self.database_connected.connect(self._put_table_names_in_combo_boxes)

        QObject.connect(self.ui.cb_table_name_municipio, QtCore.SIGNAL('currentIndexChanged (const QString&)'),
                       self._put_column_fields_in_municipio_combo_boxes)
        QObject.connect(self.ui.cb_table_name_cete, QtCore.SIGNAL('currentIndexChanged (const QString&)'),
                        self._put_column_fields_in_cete_combo_boxes)
        QObject.connect(self.ui.cb_table_name_osm, QtCore.SIGNAL('currentIndexChanged (const QString&)'),
                        self._put_column_fields_in_osm_combo_boxes)

        self.ui.bt_choose_folder.clicked.connect(self._command_open_file_dialog)

        self.ui.bt_load_municipios.clicked.connect(self._command_exec_municipio_area)
        self.ui.bt_load_roads_cete.clicked.connect(self._command_exec_cete_roads)
        self.ui.bt_load_roads_osm.clicked.connect(self._command_exec_osm_roads)
        self.ui.bt_calc_intersection.clicked.connect(self._command_exec_intersection)
        self.ui.bt_show_buffer_osm.clicked.connect(self._command_exec_buffer_osm)
        self.ui.bt_diff_osm.clicked.connect(self._command_exec_geom_diff_osm)
        self.ui.bt_compare_name_osm.clicked.connect(self._command_exec_name_compare_osm)
        self.ui.bt_show_buffer_cete.clicked.connect(self._command_exec_buffer_cete)
        self.ui.bt_diff_cete.clicked.connect(self._command_exec_geom_diff_cete)
        self.ui.bt_compare_name_cete.clicked.connect(self._command_exec_name_compare_cete)

        #self.ui.table_check_changed.connect(self.save_settings)

        # Initial Setup
        self.block_ui_for_invalid_db_connection()

        self.ui.progress_box.setVisible(False)

        if self.test_db_connection(self.connection_info):
            self.connect_db(self.connection_info)

        self.set_config_info()

    def set_config_info(self):
        table_data = Utils.Config.get('table_data') or []
        if table_data:
            row_list = [(row['geocodigo'], row['municipio_name']) for row in table_data]
            self.ui.insert(row_list)

            all_data = self.ui.get_all_data()

            def find_geocod(geocod):
                for data in table_data:
                    if geocod == data['geocodigo']:
                        return data['checked']
                return True

            for row in all_data:
                checked = find_geocod(row.get(1))
                row.select(checked)

        self.ui_db_connection.txt_host.setText(self.connection_info['host'])
        self.ui_db_connection.txt_port.setText(str(self.connection_info['port']))
        self.ui_db_connection.txt_dbname.setText(self.connection_info['dbname'])
        self.ui_db_connection.txt_user.setText(self.connection_info['user'])
        self.ui_db_connection.txt_password.setText(self.connection_info['password'])

        self.ui.txt_buffer_size.setValue(self.config_info['buffer_size'])
        self.ui.check_all_one_layer.setCheckState(Qt.Unchecked if not self.config_info['only_one_layer'] else Qt.Checked)
        self.ui.check_save_folder.setCheckState(Qt.Unchecked if not self.config_info['save_in_folder'] else Qt.Checked)
        self.block_choose_folder_button(self.config_info['save_in_folder'])

    def save_settings(self):
        Utils.Config.set('connection_info', self.connection_info)
        Utils.Config.set('municipios_info', self.municipios_info)
        Utils.Config.set('cete_info', self.cete_info)
        Utils.Config.set('osm_info', self.osm_info)
        Utils.Config.set('config_info', self.config_info)

        data = []
        for table_row in self.ui.get_all_data():
            checked = table_row.is_selected()
            row = {
                'checked': checked,
                'geocodigo': table_row.get(1),
                'municipio_name': table_row.get(2)
            }
            data.append(row)

        Utils.Config.set('table_data', data)

    def add_table_item(self, geocod_list=None):
        if not geocod_list:
            return

        # Pesquisando nome de município
        con = PostgresCon(**self.connection_info)

        s = u"SELECT {muni[geocodigo_field]}, {muni[name_field]} FROM {muni[table_name]} WHERE {muni[geocodigo_field]} IN ('{cod_list}')".format(
            muni=self.municipios_info,
            cod_list="', '".join(geocod_list))

        try:
            query = con.select(s)

            result_list = []
            while query.next():
                tup = (query.value(0), query.value(1))
                result_list.append(tup)

            # Antes de inserir verificar se é repetido
            data = self.ui.get_all_data()
            for i in range(len(data)):
                geocod = data[i].get(1)

                for i, r in enumerate(result_list):
                    r_geocod = r[0]
                    if r_geocod == geocod:
                        del result_list[i]
                        break

            self.ui.insert(result_list)

        except Exception, arg:
            Utils.Logging.warning(unicode(arg), 'OSM Plugin')
            Utils.MessageBox.warning(unicode(arg), u'Erro na consulta')

    def showView(self):
        self.ui.show()
        self.ui.exec_()

    def _put_table_names_in_combo_boxes(self):
        if not self.db_connection:
            return

        self.ui.cb_table_name_municipio.clear()
        self.ui.cb_table_name_cete.clear()
        self.ui.cb_table_name_osm.clear()

        tables = [''] + self.db_connection.get_all_tables()

        self.ui.cb_table_name_municipio.addItems(tables)
        self.ui.cb_table_name_cete.addItems(tables)
        self.ui.cb_table_name_osm.addItems(tables)

        if self.municipios_info['table_name']:
            self.ui.cb_table_name_municipio.setCurrentIndex(self.ui.cb_table_name_municipio.findText(self.municipios_info['table_name']))

        if self.cete_info['table_name']:
            self.ui.cb_table_name_cete.setCurrentIndex(self.ui.cb_table_name_cete.findText(self.cete_info['table_name']))

        if self.osm_info['table_name']:
            self.ui.cb_table_name_osm.setCurrentIndex(self.ui.cb_table_name_osm.findText(self.osm_info['table_name']))

    def _put_column_fields_in_municipio_combo_boxes(self, table_name):
        if not table_name:
            return

        if not self.test_db_connection(self.connection_info):
            self._launch_db_error()
            return

        self.ui.cb_field_name_municipio.clear()
        self.ui.cb_field_geocod_municipio.clear()
        self.ui.cb_field_geom_municipio.clear()

        columns = self.db_connection.get_columns(table_name)
        names = [''] + [name for name, data_type, udt_name in columns]

        self.ui.cb_field_name_municipio.addItems(sorted(names))
        self.ui.cb_field_geocod_municipio.addItems(sorted(names))
        self.ui.cb_field_geom_municipio.addItems(sorted(names))

        if self.municipios_info['geocodigo_field']:
            self.ui.cb_field_geocod_municipio.setCurrentIndex(self.ui.cb_field_geocod_municipio.findText(self.municipios_info['geocodigo_field']))

        if self.municipios_info['name_field']:
            self.ui.cb_field_name_municipio.setCurrentIndex(self.ui.cb_field_geocod_municipio.findText(self.municipios_info['name_field']))

        if self.municipios_info['geom_field']:
            self.ui.cb_field_geom_municipio.setCurrentIndex(self.ui.cb_field_geocod_municipio.findText(self.municipios_info['geom_field']))

    def _put_column_fields_in_cete_combo_boxes(self, table_name):
        if not table_name:
            return

        if not self.test_db_connection(self.connection_info):
            self._launch_db_error()
            return

        self.ui.cb_field_id_cete.clear()
        self.ui.cb_field_name_cete.clear()
        self.ui.cb_field_geom_cete.clear()

        columns = self.db_connection.get_columns(table_name)
        names = [''] + [name for name, data_type, udt_name in columns]

        self.ui.cb_field_id_cete.addItems(sorted(names))
        self.ui.cb_field_name_cete.addItems(sorted(names))
        self.ui.cb_field_geom_cete.addItems(sorted(names))

        if self.cete_info['name_field']:
            self.ui.cb_field_name_cete.setCurrentIndex(
                self.ui.cb_field_name_cete.findText(self.cete_info['name_field']))

        if self.cete_info['id_field']:
            self.ui.cb_field_id_cete.setCurrentIndex(
                self.ui.cb_field_id_cete.findText(self.cete_info['id_field']))

        if self.cete_info['geom_field']:
            self.ui.cb_field_geom_cete.setCurrentIndex(
                self.ui.cb_field_geom_cete.findText(self.cete_info['geom_field']))

    def _put_column_fields_in_osm_combo_boxes(self, table_name):
        if not table_name:
            return

        if not self.test_db_connection(self.connection_info):
            self._launch_db_error()
            return

        columns = self.db_connection.get_columns(table_name)
        names = [''] + [name for name, data_type, udt_name in columns]

        self.ui.cb_field_id_osm.clear()
        self.ui.cb_field_name_osm.clear()
        self.ui.cb_field_geom_osm.clear()

        self.ui.cb_field_id_osm.addItems(sorted(names))
        self.ui.cb_field_name_osm.addItems(sorted(names))
        self.ui.cb_field_geom_osm.addItems(sorted(names))
        
        if self.osm_info['name_field']:
            self.ui.cb_field_name_osm.setCurrentIndex(
                self.ui.cb_field_name_osm.findText(self.osm_info['name_field']))

        if self.osm_info['id_field']:
            self.ui.cb_field_id_osm.setCurrentIndex(
                self.ui.cb_field_id_osm.findText(self.osm_info['id_field']))

        if self.osm_info['geom_field']:
            self.ui.cb_field_geom_osm.setCurrentIndex(
                self.ui.cb_field_geom_osm.findText(self.osm_info['geom_field']))

    def _assign(self, who, index, value):
        if isinstance(value, (int, bool)):
            who[index] = value

            if who == self.config_info:
                self.save_settings()

        else:
            if not value:
                return

            who[index] = value.strip()

        self.check_block_table_buttons()
        self.check_block_operation_buttons()

    # Este método define a operação básica para execução de todas as operações da ui.
    # Se layer for None então fica implicito que a função deve criar e adicionar as camadas
    # conforme a query é finalizada. Caso contrário, o resultado da query é armazenado dentro
    # da layer passada como parâmetro.
    # Caso a layer for None, o parametro callback_layer_name é obrigatório ou um exceção é lançada.
    # @param: callback_query = função para geração da consulta do banco de dados. Cada loop executa
    #         esta função passando o geocodigo do municipio do loop atual
    # @param: callback_layer_name = uma função para customizar os nomes da camadas geradas.
    #         Os parametros passados são: nome do município e o tamanho do buffer
    def basic_query_operation(self, rows_list, callback_query, callback_layer_name=None, layer_geom_type='linestring', layer=None):
        self.save_settings()
        only_one_layer = layer is not None
        save_in_folder = self.config_info['save_in_folder']

        if only_one_layer:
            with layer:
                for index, row in enumerate(rows_list):
                    #buffer_size = self.config_info['buffer_size']
                    geocod = row.get(1)
                    muni = row.get(2)

                    query = callback_query(geocod)
                    progress = float(index) / float(len(rows_list)) * 100
                    self.progress(progress,
                                  u'Processando: {muni} ({n}/{t})'.format(muni=muni, n=index, t=len(rows_list)))

                    result_query = self.execute_thread_query(query)
                    if result_query:
                        layer.fill(result_query)
                        Utils.Logging.info(u'Feições carregadas: {}. Município: {}'.format(layer.name(), muni), 'OSM Plugin')
                    else:
                        break

            if save_in_folder:
                self.save_as_shapefile(layer, layer.name())

        else:
            for index, row in enumerate(rows_list):
                buffer_size = self.config_info['buffer_size']
                geocod = row.get(1)
                muni = row.get(2)

                layer_name = callback_layer_name(muni, buffer_size)
                layer = self.create_layer(layer_name, layer_geom_type)

                query = callback_query(geocod)

                progress = float(index) / float(len(rows_list)) * 100
                self.progress(progress, u'Processando: {muni} ({n}/{t})'.format(muni=muni, n=index, t=len(rows_list)))

                result_query = self.execute_thread_query(query)
                if result_query:
                    self.add_layer_on_qgis(layer, result_query)
                else:
                    break

                if save_in_folder:
                    self.save_as_shapefile(layer, str(geocod))

    def area_query_operation(self, rows_list=None, callback_query=None):
        self.save_settings()

        layer_name = u'Área Municípios'
        layer = self.create_layer(layer_name, 'polygon')

        with layer:
            if rows_list:
                for index, row in enumerate(rows_list):
                    geocod = row.get(1)
                    muni = row.get(2)

                    query = callback_query(geocod)

                    progress = float(index) / float(len(rows_list)) * 100
                    self.progress(progress, u'Processando: {muni} ({n}/{t})'.format(muni=muni, n=index, t=len(rows_list)))

                    result_query = self.execute_thread_query(query)
                    layer.fill(result_query)

            else:
                query = callback_query('')

                self.progress(0, u'Processando')

                result_query = self.execute_thread_query(query)
                layer.fill(result_query)

        self.add_layer_on_qgis(layer)

    def _command_show_db_info(self):
        self.ui_db_connection.show()
        self.ui_db_connection.exec_()

    def _command_show_geocods_dialog(self):
        self.ui_geocods.show()
        self.ui_geocods.exec_()

    def _command_connect_db(self):
        self.connection_info = {
            "host": self.ui_db_connection.txt_host.text(),
            "password": self.ui_db_connection.txt_password.text(),
            "user": self.ui_db_connection.txt_user.text(),
            "dbname": self.ui_db_connection.txt_dbname.text(),
            "port": int(self.ui_db_connection.txt_port.text())}
        self.connect_db(self.connection_info)

    def _command_add_geocods(self):
        if not self.is_db_connection_ok:
            Utils.MessageBox.critical(u'Não foi possível estabelecer conexão com o banco de dados', 'Falha')
            return

        geocod_list = self.ui_geocods.geocod_list()

        if not geocod_list:
            return

        self.add_table_item(geocod_list)

    def _command_exec_municipio_area(self):
        if not self.test_db_connection(self.connection_info):
            self._launch_db_error()
            return

        self.block_ui_for_operation(True)

        # Comentado para só carregar todas as áreas da tabela

        #rows_list = self.ui.get_all_selected_data()

        # if rows_list:
        #     callback_query = lambda geocod: u"""
        #         SELECT {muni[geocodigo_field]}, {muni[name_field]}, {muni[geom_field]} FROM {muni[table_name]} as muni
        #         WHERE {muni[geocodigo_field]} = {geocodigo}::text
        #     """.format(muni=self.municipios_info, geocodigo=geocod)
        # else:
        callback_query = lambda geocod: u"""
            SELECT {muni[geocodigo_field]}, {muni[name_field]}, {muni[geom_field]} 
            FROM {muni[table_name]}
        """.format(muni=self.municipios_info)

        self.area_query_operation(callback_query=callback_query)

        self.block_ui_for_operation(False)

    def _command_exec_cete_roads(self):
        if not self.test_db_connection(self.connection_info):
            self._launch_db_error()
            return

        self.block_ui_for_operation(True)

        rows_list = self.ui.get_all_selected_data()

        callback_query = self.query_cete_roads
        callback_layer_name = lambda muni, buffer_size: u"CETE: " + muni

        if self.config_info['only_one_layer']:
            layer_name = u'CETE eixos'
            layer = self.create_layer(layer_name)

            self.add_layer_on_qgis(layer)

            self.basic_query_operation(rows_list, callback_query, layer=layer)
        else:
            self.basic_query_operation(rows_list, callback_query, callback_layer_name)

        self.block_ui_for_operation(False)

    def _command_exec_osm_roads(self):
        if not self.test_db_connection(self.connection_info):
            self._launch_db_error()
            return

        self.block_ui_for_operation(True)

        rows_list = self.ui.get_all_selected_data()

        callback_query = self.query_osm_roads
        callback_layer_name = lambda muni, buffer_size: u"OSM: " + muni

        if self.config_info['only_one_layer']:
            layer_name = u'OSM eixos'
            layer = self.create_layer(layer_name)

            self.add_layer_on_qgis(layer)

            self.basic_query_operation(rows_list, callback_query, layer=layer)
        else:
            self.basic_query_operation(rows_list, callback_query, callback_layer_name)

        self.block_ui_for_operation(False)

    def _command_exec_intersection(self):
        if not self.test_db_connection(self.connection_info):
            self._launch_db_error()
            return

        self.block_ui_for_operation(True)

        rows_list = self.ui.get_all_selected_data()

        callback_query = self.query_intersection
        callback_layer_name = lambda muni, buffer_size: u'Intersection {}m: {}'.format(buffer_size, muni)

        if self.config_info['only_one_layer']:
            layer_name = u'Intersecao {}m'.format(self.config_info['buffer_size'])
            layer = self.create_layer(layer_name)

            self.add_layer_on_qgis(layer)

            self.basic_query_operation(rows_list, callback_query, layer=layer)
        else:
            self.basic_query_operation(rows_list, callback_query, callback_layer_name)

        self.block_ui_for_operation(False)

    def _command_exec_buffer_osm(self):
        if not self.test_db_connection(self.connection_info):
            self._launch_db_error()
            return

        self.block_ui_for_operation(True)

        rows_list = self.ui.get_all_selected_data()

        callback_query = self.query_osm_buffer
        callback_layer_name = lambda muni, buffer_size: u'OSM Buffer {}m: {}'.format(buffer_size, muni)

        if self.config_info['only_one_layer']:
            layer_name = u'OSM Buffer {}m'.format(self.config_info['buffer_size'])
            layer = self.create_layer(layer_name, 'polygon')

            self.add_layer_on_qgis(layer)

            self.basic_query_operation(rows_list, callback_query, layer=layer)
        else:
            self.basic_query_operation(rows_list, callback_query, callback_layer_name, layer_geom_type='polygon')

        self.block_ui_for_operation(False)

    def _command_exec_geom_diff_osm(self):
        if not self.test_db_connection(self.connection_info):
            self._launch_db_error()
            return

        self.block_ui_for_operation(True)

        rows_list = self.ui.get_all_selected_data()

        callback_query = self.query_osm_diff
        callback_layer_name = lambda muni, buffer_size: u'OSM Diff {}m: {}'.format(buffer_size, muni)

        if self.config_info['only_one_layer']:
            layer_name = u'OSM Diff {}m'.format(self.config_info['buffer_size'])
            layer = self.create_layer(layer_name)

            self.add_layer_on_qgis(layer)

            self.basic_query_operation(rows_list, callback_query, layer=layer)
        else:
            self.basic_query_operation(rows_list, callback_query, callback_layer_name)

        self.block_ui_for_operation(False)

    def _command_exec_name_compare_osm(self):
        if not self.test_db_connection(self.connection_info):
            self._launch_db_error()
            return

        self.block_ui_for_operation(True)

        rows_list = self.ui.get_all_selected_data()

        callback_query = self.query_exclusive_osm_name
        callback_layer_name = lambda muni, buffer_size: u'OSM NameComparacao: {}'.format(muni)

        if self.config_info['only_one_layer']:
            layer_name = u'OSM NameComparacao'.format(self.config_info['buffer_size'])
            layer = self.create_layer(layer_name)

            self.add_layer_on_qgis(layer)

            self.basic_query_operation(rows_list, callback_query, layer=layer)
        else:
            self.basic_query_operation(rows_list, callback_query, callback_layer_name)

        self.block_ui_for_operation(False)

    def _command_exec_buffer_cete(self):
        if not self.test_db_connection(self.connection_info):
            self._launch_db_error()
            return

        self.block_ui_for_operation(True)

        rows_list = self.ui.get_all_selected_data()

        callback_query = self.query_cete_buffer
        callback_layer_name = lambda muni, buffer_size: u'CETE Buffer {}m: {}'.format(buffer_size, muni)

        if self.config_info['only_one_layer']:
            layer_name = u'CETE Buffer {}m'.format(self.config_info['buffer_size'])
            layer = self.create_layer(layer_name, 'polygon')

            self.add_layer_on_qgis(layer)

            self.basic_query_operation(rows_list, callback_query, layer=layer)
        else:
            self.basic_query_operation(rows_list, callback_query, callback_layer_name, layer_geom_type='polygon')

        self.block_ui_for_operation(False)

    def _command_exec_geom_diff_cete(self):
        if not self.test_db_connection(self.connection_info):
            self._launch_db_error()
            return

        self.block_ui_for_operation(True)

        rows_list = self.ui.get_all_selected_data()

        callback_query = self.query_cete_diff
        callback_layer_name = lambda muni, buffer_size: u'CETE Diff {}m: {}'.format(buffer_size, muni)

        if self.config_info['only_one_layer']:
            layer_name = u'CETE Diff {}m'.format(self.config_info['buffer_size'])
            layer = self.create_layer(layer_name)

            self.add_layer_on_qgis(layer)

            self.basic_query_operation(rows_list, callback_query, layer=layer)
        else:
            self.basic_query_operation(rows_list, callback_query, callback_layer_name)

        self.block_ui_for_operation(False)

    def _command_exec_name_compare_cete(self):
        if not self.test_db_connection(self.connection_info):
            self._launch_db_error()
            return

        self.block_ui_for_operation(True)

        rows_list = self.ui.get_all_selected_data()

        callback_query = self.query_exclusive_cete_name
        callback_layer_name = lambda muni, buffer_size: u'CETE NameComparacao: {}'.format(muni)

        if self.config_info['only_one_layer']:
            layer_name = u'CETE NameComparacao {}m'.format(self.config_info['buffer_size'])
            layer = self.create_layer(layer_name)

            self.add_layer_on_qgis(layer)

            self.basic_query_operation(rows_list, callback_query, layer=layer)
        else:
            self.basic_query_operation(rows_list, callback_query, callback_layer_name)

        self.block_ui_for_operation(False)

    def _command_open_file_dialog(self):
        dialog = QtGui.QFileDialog()

        dialog.setFileMode(QtGui.QFileDialog.Directory)

        output_folder = QtGui.QFileDialog.getExistingDirectory(None, u"Selecione pasta de saída", self.config_info['output_folder'] or "C:/")

        self.config_info['output_folder'] = output_folder if output_folder else self.config_info['output_folder']
        self.save_settings()

    # Progress Bar
    def progress(self, progress_value, progress_status_msg):
        self.ui.progress_bar.setValue(progress_value)
        self.ui.progress_status.setText(progress_status_msg)

    # Testa a conexão com banco de dados. Se estiver ok, retorna uma conexão caso contrário False
    def test_db_connection(self, connection_info=None):
        if not connection_info:
            return False

        con = PostgresCon(**connection_info)
        
        result = con.open()

        if result:
            con.close()

            self.check_block_table_buttons()
            self.check_block_operation_buttons()

            return con

        return False

    def _launch_db_error(self):
        self.ui.lb_connected.setText(u'Conectado a:')
        Utils.Logging.critical(u'Não foi possível estabelecer conexão com o banco de dados', 'OSM Plugin')
        Utils.MessageBox.critical(u'Não foi possível estabelecer conexão com o banco de dados', 'Falha')

        # Se não conectado ao banco de dados, não permitir demais operações
        self.is_db_connection_ok = False
        self.block_ui_for_invalid_db_connection()

    def block_ui_for_invalid_db_connection(self, bool_=True):
        self.ui.municipios_box.setEnabled(not bool_)
        self.ui.operations_box.setEnabled(not bool_)
        self.ui.table_cete_box.setEnabled(not bool_)
        self.ui.table_osm_box.setEnabled(not bool_)
        self.block_table_buttons(bool_)

    def block_table_buttons(self, bool_=True):
        self.ui.bt_table_add.setEnabled(not bool_)
        self.ui.bt_table_remove.setEnabled(not bool_)
        self.ui.bt_table_select_all.setEnabled(not bool_)
        self.ui.bt_table_deselect_all.setEnabled(not bool_)

    def block_ui_for_operation(self, bool_=True):
        self.ui.bt_database_connection.setEnabled(not bool_)
        self.ui.municipios_box.setEnabled(not bool_)
        self.ui.operations_box.setEnabled(not bool_)
        self.ui.table_cete_box.setEnabled(not bool_)
        self.ui.table_osm_box.setEnabled(not bool_)
        self.ui.config_box.setEnabled(not bool_)
        self.block_table_buttons(bool_)
        self.ui.setProgressVisible(bool_)

    def block_operations_buttons(self, bool_=True):
        self.ui.operations_box.setEnabled(not bool_)

    def check_block_table_buttons(self):
        for field, value in self.municipios_info.items():
            if not value:
                self.block_table_buttons(True)
                return False

        self.block_table_buttons(False)
        return True

    def check_block_operation_buttons(self):
        for field, value in self.municipios_info.items():
            if not value:
                self.block_operations_buttons(True)
                return False

        for field, value in self.cete_info.items():
            if not value:
                self.block_operations_buttons(True)
                return False

        for field, value in self.osm_info.items():
            if not value:
                self.block_operations_buttons(True)
                return False

        self.block_operations_buttons(False)
        return True

    def block_choose_folder_button(self, bool_=True):
        self.ui.bt_choose_folder.setEnabled(bool_)

    def connect_db(self, connection_info=None):
        if connection_info is None:
            return False
        
        con = self.test_db_connection(connection_info)
        
        if con:
            self.db_connection = con
            self.connection_info = connection_info

            self.ui.lb_connected.setText(u'Conectado a: {dbname} em {host}'.format(
                dbname=self.db_connection.databaseName(),
                host=self.db_connection.hostName()
            ))

            self.ui.municipios_box.setEnabled(True)
            self.ui.table_cete_box.setEnabled(True)
            self.ui.table_osm_box.setEnabled(True)

            self.is_db_connection_ok = True
            self.database_connected.emit()

        else:
            self._launch_db_error()

    def save_as_shapefile(self, layer, file_name):
        dir = self.config_info['output_folder']
        path = dir + '/' + file_name + '.shp'

        QgsVectorFileWriter.writeAsVectorFormat(layer, path, "utf-8", layer.crs(), "ESRI Shapefile")

    def add_layer_on_qgis(self, layer, result_query=None):
        Utils.Logging.info(u'Adicionando camada: ' + layer.name(), 'OSM Plugin')

        Utils.Layer.add(layer)

        if result_query:
            layer.append(result_query)
            Utils.Logging.info(u'Feições carregadas: ' + layer.name(), 'OSM Plugin')

    def execute_thread_query(self, query):
        if self.db_connection:
            query = u'(SELECT row_number() over() as _uid_, * FROM ( {} ) AS sub_qry1)'.format(query)

            # Cria um callback para ser executado na thread
            exec_query = lambda: self.db_connection.select(query)

            task = Task(exec_query)

            try:
                task.start()

                if task.error:
                    raise Exception

                return task.result

            except:
                Utils.MessageBox.warning(unicode(task.error[0]), 'Erro')
                return None

        self.block_ui_for_operation(False)

        Utils.MessageBox.critical(u'Conexão com o banco de dados nula. Verifique a conexão.', u'Erro ao conectar banco de dados')
        raise Exception(u'Database connection is null')

    def create_layer(self, layer_name='', geom_type='linestring'):
        uri = QgsDataSourceURI()
        info = self.connection_info
        uri.setConnection(info['host'], str(info['port']), info['dbname'], info['user'], info['password'], QgsDataSourceURI.SSLdisable)
        uri.setKeyColumn('_uid_')
        uri.setParam('geom_type', geom_type)

        layer = QueryMemoryLayer(uri, layer_name, query='')
        return layer

    def query_cete_roads(self, geocod):
        query = u"""
            SELECT roads.{cete[id_field]} as gid, roads.{cete[name_field]} AS name, {geocodigo} AS geocodigo, ST_asBinary(roads.{cete[geom_field]}) AS geom 
            FROM {cete[table_name]} AS roads, {muni[table_name]} AS muni
            WHERE st_contains(muni.{muni[geom_field]}, roads.{cete[geom_field]}) 
                AND muni.{muni[geocodigo_field]}::text = {geocodigo}::text
        """.format(
            cete=self.cete_info, muni=self.municipios_info, geocodigo=geocod
        )

        return query

    def query_osm_roads(self, geocod):
        query = u"""
            SELECT roads.{osm[id_field]} as gid, roads.{osm[name_field]} AS name, {geocodigo} AS geocodigo, ST_asBinary(roads.{osm[geom_field]}) AS geom 
            FROM {osm[table_name]} AS roads, {muni[table_name]} AS muni
            WHERE st_contains(muni.{muni[geom_field]}, roads.{osm[geom_field]}) 
                AND muni.{muni[geocodigo_field]}::text = {geocodigo}::text
        """.format(
            osm=self.osm_info, muni=self.municipios_info, geocodigo=geocod
        )

        return query

    def query_intersection(self, geocod):
        query = u"""
            WITH 
            params(geocodigo, buffer_size) AS (VALUES({geocodigo}::text, {buffer_size}::double precision)),
            muni AS
            (
                SELECT {municipios[geocodigo_field]} AS cd_geocodigo, {municipios[geom_field]} AS gm_area
                FROM params, {municipios[table_name]}
                WHERE {municipios[geocodigo_field]} = params.geocodigo
            ),
            osm_roads AS
            (
                SELECT roads.{osm_roads[id_field]} AS gid, roads.{osm_roads[name_field]} AS name, roads.{osm_roads[geom_field]} AS geom
                FROM {osm_roads[table_name]} as roads, muni
                WHERE st_contains(muni.gm_area, roads.{osm_roads[geom_field]})
            ),
            cete_roads AS
            (
                SELECT roads.{cete_roads[id_field]} AS gid, roads.{cete_roads[name_field]} AS name, roads.{cete_roads[geom_field]} AS geom
                FROM {cete_roads[table_name]} AS roads, muni
                WHERE st_contains(muni.gm_area, roads.{cete_roads[geom_field]})
            ),
            osm_buffer AS
            (
                SELECT osm.gid, osm.name, st_buffer(osm.geom, params.buffer_size, 4) AS geom
                FROM params, osm_roads osm
            )

            SELECT 
                row_number() over() as id,
                b.cete_gid, b.cete_logradouro::text,
                b.osm_gid, b.osm_logradouro::text,
                {geocodigo} AS geocodigo,
                ST_asBinary(b.geom) AS geom
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
            geocodigo=geocod,
            buffer_size=self.buffer_to_degree(),
            municipios=self.municipios_info,
            osm_roads=self.osm_info,
            cete_roads=self.cete_info
        )

        return query

    # query_intersection_modified method is used in another methods to compound its logic. This method is modified to return a binary geometry
    # to not generate a bug with incompatible srid
    def query_intersection_modified(self, geocod):
        query = u"""
            WITH 
            params(geocodigo, buffer_size) AS (VALUES({geocodigo}::text, {buffer_size}::double precision)),
            muni AS
            (
                SELECT {municipios[geocodigo_field]} AS cd_geocodigo, {municipios[geom_field]} AS gm_area
                FROM params, {municipios[table_name]}
                WHERE {municipios[geocodigo_field]} = params.geocodigo
            ),
            osm_roads AS
            (
                SELECT roads.{osm_roads[id_field]} AS gid, roads.{osm_roads[name_field]} AS name, roads.{osm_roads[geom_field]} AS geom
                FROM {osm_roads[table_name]} as roads, muni
                WHERE st_contains(muni.gm_area, roads.{osm_roads[geom_field]})
            ),
            cete_roads AS
            (
                SELECT roads.{cete_roads[id_field]} AS gid, roads.{cete_roads[name_field]} AS name, roads.{cete_roads[geom_field]} AS geom
                FROM {cete_roads[table_name]} AS roads, muni
                WHERE st_contains(muni.gm_area, roads.{cete_roads[geom_field]})
            ),
            osm_buffer AS
            (
                SELECT osm.gid, osm.name, st_buffer(osm.geom, params.buffer_size, 4) AS geom
                FROM params, osm_roads osm
            )

            SELECT 
                row_number() over() as id,
                b.cete_gid, b.cete_logradouro::text,
                b.osm_gid, b.osm_logradouro::text,
                {geocodigo} AS geocodigo,
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
            geocodigo=geocod,
            buffer_size=self.buffer_to_degree(),
            municipios=self.municipios_info,
            osm_roads=self.osm_info,
            cete_roads=self.cete_info
        )

        return query

    def query_osm_buffer(self, geocod):
        query = u"""
            SELECT roads.{osm_roads[id_field]}, roads.{osm_roads[name_field]}, {geocodigo} AS geocodigo, ST_asBinary(st_buffer(roads.{osm_roads[geom_field]}, {buffer_size})) AS geom 
            FROM 
                {osm_roads[table_name]} AS roads,
                {municipios[table_name]} AS muni 
            WHERE st_contains(muni.{municipios[geom_field]}, roads.{osm_roads[geom_field]}) 
            AND muni.{municipios[geocodigo_field]}::text = {geocodigo}::text
        """.format(
            geocodigo=geocod,
            osm_roads=self.osm_info,
            buffer_size=self.buffer_to_degree(),
            municipios=self.municipios_info,
        )

        return query

    def query_cete_buffer(self, geocod):
        query = u"""
            SELECT roads.{cete_roads[id_field]} AS gid, roads.{cete_roads[name_field]} AS name, {geocodigo} AS geocodigo, ST_asBinary(st_buffer(roads.{cete_roads[geom_field]}, {buffer_size})) AS geom 
            FROM 
                {cete_roads[table_name]} AS roads, 
                {municipios[table_name]} AS muni 
            WHERE st_contains(muni.{municipios[geom_field]}, roads.{cete_roads[geom_field]}) 
            AND muni.{municipios[geocodigo_field]}::text = {geocodigo}::text
        """.format(
            geocodigo=geocod,
            cete_roads=self.cete_info,
            buffer_size=self.buffer_to_degree(),
            municipios=self.municipios_info,
        )

        return query

    def query_osm_diff(self, geocod):
        query = u"""
            WITH
            params(geocodigo, buffer_size) AS (VALUES({geocodigo}, {buffer_size})),
            muni AS (
                SELECT {municipios[geocodigo_field]} AS cd_geocodigo, {municipios[geom_field]} AS gm_area
                FROM {municipios[table_name]}, params
                WHERE {municipios[geocodigo_field]} = params.geocodigo::text
            ),
            osm AS (
                SELECT roads.{osm_roads[id_field]} AS gid, roads.{osm_roads[name_field]} AS name, roads.{osm_roads[geom_field]} AS geom
                FROM {osm_roads[table_name]} AS roads, muni
                WHERE ST_Within(roads.{osm_roads[geom_field]}, muni.gm_area)
            ),
            inter AS (
                SELECT st_union(st_buffer(i.geom::geometry, params.buffer_size::double precision, 4)) AS geom
                FROM params, LATERAL ( {intersection_query} ) AS i
            ),
            quick_diff AS (
                SELECT osm.gid, osm.name, osm.geom AS geom
                FROM osm, inter
                WHERE NOT ST_Within(osm.geom, inter.geom)
            )
    
            SELECT diff.gid, diff.name AS logradouro, {geocodigo} AS geocodigo, ST_asBinary(ST_Difference(diff.geom, inter.geom)) AS geom
            FROM quick_diff as diff, inter
            WHERE ST_Intersects(diff.geom, inter.geom)
    
            UNION
    
            SELECT diff.gid, diff.name AS logradouro, {geocodigo} AS geocodigo, ST_asBinary(diff.geom) AS geom
            FROM quick_diff AS diff, inter
            WHERE NOT ST_Intersects(diff.geom, inter.geom)
        """.format(
            geocodigo=geocod,
            osm_roads=self.osm_info,
            buffer_size=self.buffer_to_degree(),
            intersection_query=self.query_intersection_modified(geocod),
            municipios=self.municipios_info,
        )

        return query

    def query_cete_diff(self, geocod):
        query = u""" 
        WITH
        params(geocodigo, buffer_size) AS (VALUES({geocodigo}, {buffer_size})),
        muni AS (
            SELECT {municipios[geocodigo_field]} AS cd_geocodigo, {municipios[geom_field]} AS gm_area
            FROM {municipios[table_name]}, params
            WHERE {municipios[geocodigo_field]} = params.geocodigo::text
        ),
        cete AS (
            SELECT c.{cete_roads[id_field]} AS gid, c.{cete_roads[name_field]} AS name, c.{cete_roads[geom_field]} AS geom
            FROM {cete_roads[table_name]} AS c, muni
            WHERE ST_Within(c.{cete_roads[geom_field]}, muni.gm_area)
        ),
        inter AS (
            SELECT st_union(st_buffer(i.geom::geometry, params.buffer_size::double precision, 4)) AS geom
            FROM params, LATERAL ( {intersection_query} ) AS i
        ),
        quick_diff AS (
            SELECT cete.gid, cete.name, cete.geom AS geom
            FROM cete, inter
            WHERE NOT ST_Within(cete.geom, inter.geom)
        )

        SELECT diff.gid, diff.name AS logradouro, {geocodigo} AS geocodigo, ST_asBinary(st_difference(diff.geom, inter.geom)) AS geom
        FROM quick_diff AS diff, inter
        WHERE ST_Intersects(diff.geom, inter.geom)

        UNION

        SELECT diff.gid, diff.name AS logradouro, {geocodigo} AS geocodigo, ST_asBinary(diff.geom) AS geom 
        FROM quick_diff AS diff, inter
        WHERE NOT ST_Intersects(diff.geom, inter.geom)
        """.format(
            geocodigo=geocod,
            cete_roads=self.cete_info,
            buffer_size=self.buffer_to_degree(),
            intersection_query=self.query_intersection_modified(geocod),
            municipios=self.municipios_info,
        )

        return query

    def query_exclusive_osm_name(self, geocod):
        query = u"""
            SELECT * 
            FROM 
                ( {intersection_query} ) AS i
            WHERE
                (cete_logradouro IS NULL OR cete_logradouro ILIKE '%sem nome%' OR cete_logradouro ILIKE '%sem ident%' OR cete_logradouro ILIKE '%sem denomina%') AND osm_logradouro IS NOT NULL
        """.format(
            intersection_query=self.query_intersection_modified(geocod)
        )

        return query

    def query_exclusive_cete_name(self, geocod):
        query = u"""
            SELECT * 
            FROM 
                ( {intersection_query} ) AS i
            WHERE
                (osm_logradouro IS NULL OR osm_logradouro ILIKE '%sem nome%' OR osm_logradouro ILIKE '%sem ident%' OR osm_logradouro ILIKE '%sem denomina%') AND cete_logradouro IS NOT NULL
        """.format(
            intersection_query=self.query_intersection_modified(geocod)
        )

        return query

    def buffer_to_degree(self):
        return float(self.config_info['buffer_size']) / 111000.0





FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'dialog_base_v2.ui'))

class BaseDialog(QtGui.QDialog, FORM_CLASS):
    table_check_changed = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(BaseDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        self.table_model = TableModel()
        self.table_municipios.setModel(self.table_model)

        # Resize campo checkbox
        self.table_municipios.horizontalHeader().setResizeMode(0, 3) # 0 = Coluna 0. 3 = Resize mode QHeaderView.ResizeToContents
        # Resize campo municipio
        self.table_municipios.horizontalHeader().setResizeMode(2, 1) # 2 = Coluna 2. 1 = Resize mode QHeaderView.Stretch

        self.table_model.check_changed.connect(self.table_check_changed)

    def setProgressVisible(self, b):
        self.progress_box.setVisible(b)
        self.adjustSize()
        self.progress_bar.setValue(0)

    def insert(self, items_list=None):
        if not items_list:
            return

        for item in items_list:
            geocod = item[0]
            muni = item[1]

            # Colocando itens na tabela
            self.table_model.insertRows(0, 1, QModelIndex())

            index = self.table_model.createIndex(0, 1)
            self.table_model.setData(index, geocod)

            index = self.table_model.createIndex(0, 2)
            self.table_model.setData(index, muni)

    def get_all_data(self):
        return self.table_model._data

    def get_all_selected_data(self):
        return [row for row in self.get_all_data() if row.is_selected()]

    def get_all_geocods(self):
        return [row.get(1) for row in self.get_all_data()]

    def get_all_selected_geocods(self):
        return [row.get(1) for row in self.get_all_selected_data()]

    def select_all_table(self):
        data = self.get_all_data()
        for i, row in enumerate(data):
            self.table_model.setData(self.table_model.createIndex(i, 0), Qt.Checked, Qt.CheckStateRole)

    def deselect_all_table(self):
        data = self.get_all_data()
        for i, row in enumerate(data):
            self.table_model.setData(self.table_model.createIndex(i, 0), Qt.Unchecked, Qt.CheckStateRole)

    def delete_from_table(self):
        data = self.get_all_data()

        for i in range(len(data)):
            for i_, d in enumerate(data):
                if d.is_selected():
                    self.table_model.removeRows(i_, 1)





from PyQt4.QtCore import QModelIndex, QAbstractTableModel
from PyQt4.QtGui import QStandardItem

class TableModel(QAbstractTableModel):
    check_changed = pyqtSignal()
    def __init__(self):
        super(TableModel, self).__init__()

        self._data = []

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        if index.row() < 0 or index.row() >= len(self._data):
            return None

        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter

        if role == Qt.CheckStateRole:
            if index.column() == 0:
                checkbox = self._data[index.row()].get(0)
                return checkbox.checkState()

        if role == Qt.DisplayRole:
            row_idx = index.row()
            col_idx = index.column()

            row = self._data[row_idx]

            return row.get(col_idx)

        return None

    def get_row(self, pos):
        return self._data[pos]

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return 3

    def headerData(self, section, orientation, role):
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Horizontal:
            columns = [u'Sel.', u'Geocódigo', u'Município']
            if section < len(columns):
                return columns[section]

        return None

    def insertRows(self, position, rows, index=QModelIndex()):
        self.beginInsertRows(index, position, position + rows - 1)

        for row in range(rows):
            self._data.insert(position, TableRow())

        self.endInsertRows()
        return True

    def removeRows(self, position, rows, index=QModelIndex()):
        self.beginRemoveRows(index, position, position + rows - 1)

        del self._data[position]

        self.endRemoveRows()
        return True

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid():
            return False

        if role == Qt.CheckStateRole:
            self._data[index.row()].select(False if value == Qt.Unchecked else True)

            self.dataChanged.emit(index, index)
            self.check_changed.emit()
            return True

        if role == Qt.EditRole:
            row_index = index.row()

            row = self._data[row_index]

            row.set(index.column(), value)

            self.dataChanged.emit(index, index)
            return True

        return False

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled

        if index.column() == 0:
            return Qt.ItemIsEnabled | Qt.ItemIsUserCheckable

        else:
            return Qt.ItemIsEnabled #super(TableModel, self).flags(index) or Qt.ItemIsEditable


class TableRow(QObject):
    def __init__(self):
        super(TableRow, self).__init__()

        self.check = QStandardItem()
        self.select()

        self.row = [self.check, '', '']

    def select(self, bool_=True):
        self.check.setCheckable(bool_)
        if bool_:
            self.check.setCheckState(Qt.Checked)
        else:
            self.check.setCheckState(Qt.Unchecked)

    def is_selected(self):
        return False if self.check.checkState() == Qt.Unchecked else True

    def get(self, pos):
        if pos < len(self.row):
            return self.row[pos]

        return None

    def set(self, pos, value):
        if pos < len(self.row):
            self.row[pos] = value

