# -*- coding: utf-8 -*-
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

from PyQt4 import QtGui, uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'dialog_base.ui'))


class BaseDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent = None):
        """Constructor."""
        super(BaseDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

    def setProgressVisible(self, b):
        self.progress_box.setVisible(b)
        self.adjustSize()
        self.get_progress_bar().setValue(0)

    def host(self):
        return self.text_host.text()

    def port(self):
        return self.text_port.text()

    def dbName(self):
        return self.text_dbname.text()

    def user(self):
        return self.text_user.text()

    def password(self):
        return self.text_password.text()

    def osmTable(self):
        return self.text_osm_table.text()

    def ceteTable(self):
        return self.text_cete_table.text()

    def geocod(self):
        return self.text_geocod.text()

    def bufferSize(self):
        return self.text_buffer_size.text()

    def getBtShowCete(self):
        return self.bt_show_cete

    def getBtShowOsm(self):
        return self.bt_show_osm

    def getBtIntersection(self):
        return self.bt_intersection

    def getBtOsmMinusIntersection(self):
        return self.bt_osm_minus_intersection

    def getBtCeteMinusIntersection(self):
        return self.bt_cete_minus_intersection

    def getBtShowBuffer(self):
        return self.bt_show_buffer

    def getBtCeteQuickDiff(self):
        return self.bt_quick_cete_diff

    def getBtOsmQuickDiff(self):
        return self.bt_quick_osm_diff

    def getBtOsmVerifyNames(self):
        return self.bt_osm_verify_names


    #Groups
    def get_button_box(self):
        return self.button_box

    def get_progress_box(self):
        return self.progress_box

    def get_table_box(self):
        return self.table_box


    # Progress bar
    def get_progress_bar(self):
        return self.progress_bar

    def get_progress_label(self):
        return self.progress_label