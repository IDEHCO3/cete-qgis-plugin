
# coding: utf-8

import os

from PyQt4 import QtGui, uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'dialog_db_info.ui'))

class BaseDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None, connection_info=None):
        """Constructor."""
        super(BaseDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        if connection_info:
            self.txt_host.setText(connection_info['host'])
            self.txt_port.setText(connection_info['port'])
            self.txt_dbname.setText(connection_info['dbname'])
            self.txt_user.setText(connection_info['user'])
            self.txt_password.setText(connection_info['password'])
