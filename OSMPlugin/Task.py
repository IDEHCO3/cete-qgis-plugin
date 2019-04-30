
# coding: utf-8

import traceback

from qgis.utils import iface

from PyQt4.QtCore import QThread, QObject, QEventLoop, pyqtSignal


class Task(QObject):
    started = pyqtSignal()
    finished = pyqtSignal(object)

    def __init__(self, callback, *args, **kwargs):
        super(Task, self).__init__()

        self._callback = callback
        self._args = args
        self._kwargs = kwargs
        self.result = None
        self.error = None

        self.thread = QThread(iface.mainWindow())
        self.thread.run = self.run
        self.thread.finished.connect(self.exit_loop)

        self.loop = QEventLoop()

    def run(self):
        try:
            self.result = self._callback(*self._args, **self._kwargs)

        except Exception, e:
            self.error = (e, traceback.format_exc())
            self.exit_loop()
            self.thread.quit()

    def start(self):
        self.started.emit()
        self.moveToThread(self.thread)
        self.thread.start()

        self.loop.exec_()

    def exit_loop(self):
        self.loop.exit()
        self.finished.emit(self.result)
