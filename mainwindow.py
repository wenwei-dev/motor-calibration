import os
import logging
import yaml
from PyQt4 import QtCore
from PyQt4 import QtGui
from ui.mainwindow import Ui_MainWindow
from MotorItemModel import MotorItemModel, MotorValueDelegate

logger = logging.getLogger(__name__)

class MainWindow(QtGui.QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.actionExit.triggered.connect(self.close)
        self.ui.actionLoad_motor_settings.triggered.connect(self.load_motor_settings_dialog)
        filename = '/home/wenwei/motors_settings.yaml'
        self.load_motor_settings(filename)

    def close(self):
        super(MainWindow, self).close()

    def load_motor_settings_dialog(self):
        dialog = QtGui.QFileDialog(self, filter='*.yaml')
        dialog.show()
        dialog.fileSelected.connect(self.load_motor_settings)

    def load_motor_settings(self, filename):
        logger.info("Load motor settings {}".format(filename))
        with open(filename) as f:
            motors = yaml.load(f)
            model = MotorItemModel(motors)
            delegate = MotorValueDelegate(model)
            self.ui.tableView.setModel(model)
            self.ui.tableView.verticalHeader().hide()
            self.ui.tableView.setItemDelegateForColumn(5, delegate)
            self.ui.tableView.setColumnWidth(5, 800)
            for row in range(model.rowCount(QtCore.QModelIndex())):
                index = model.createIndex(row, 5)
                self.ui.tableView.openPersistentEditor(index)
