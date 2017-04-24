import os
import logging
from PyQt4 import QtCore
from PyQt4 import QtGui
from mainwindow_ui import Ui_MainWindow

logger = logging.getLogger(__name__)

class MainWindow(QtGui.QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.ui_controller = Ui_MainWindow()
        self.ui_controller.setupUi(self)
