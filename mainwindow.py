import os
import logging
import yaml
from PyQt4 import QtCore
from PyQt4 import QtGui
from ui.mainwindow import Ui_MainWindow
from MotorItemModel import MotorItemModel, MotorValueDelegate
from MotorTreeModel import MotorTreeModel

logger = logging.getLogger(__name__)

class MainWindow(QtGui.QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.init_menu()
        self.init_action()
        self.ui.actionExit.triggered.connect(self.close)
        self.ui.actionLoad_motor_settings.triggered.connect(self.load_motor_settings_dialog)
        filename = '/home/wenwei/motors_settings.yaml'
        self.load_motor_settings(filename)
        self.motors = []

    def init_menu(self):
        self.treeMenu = QtGui.QMenu(self.ui.treeView)
        self.treeMenu.addAction(self.ui.actionTuneMotors)
        self.ui.actionTuneMotors.triggered.connect(self.tuneMotors)

    def init_action(self):
        self.ui.saveButton.clicked.connect(self.saveMotors)

    def close(self):
        super(MainWindow, self).close()

    def load_motor_settings_dialog(self):
        dialog = QtGui.QFileDialog(self, filter='*.yaml')
        dialog.show()
        dialog.fileSelected.connect(self.load_motor_settings)

    def saveMotors(self):
        print self.ui.tableView.model().motors

    def tuneMotors(self):
        indexes = self.ui.treeView.selectedIndexes()
        motors = []
        for index in indexes:
            node = self.ui.treeView.model().itemFromIndex(index)
            motor = node.data().toPyObject()
            if motor:
                motor = motor[0]
                motors.append(motor)
        self.addMotorsToController(motors)

    def addMotorsToController(self, motors):
        model = MotorItemModel()
        for motor in motors:
            model.addMotor(motor)
        delegate = MotorValueDelegate(model)
        self.ui.tableView.setModel(model)
        self.ui.tableView.verticalHeader().hide()
        editor_index = model.header.index('Editor')
        self.ui.tableView.setItemDelegateForColumn(editor_index, delegate)
        self.ui.tableView.setColumnWidth(editor_index, 800)
        for row in range(model.rowCount(QtCore.QModelIndex())):
            index = model.createIndex(row, editor_index)
            self.ui.tableView.openPersistentEditor(index)

    def onTreeViewContextMenu(self, point):
        index = self.ui.treeView.indexAt(point)
        if index.isValid():
            global_point = self.ui.treeView.mapToGlobal(point)
            self.treeMenu.exec_(global_point)

    def showMotorProperty(self, index):
        node = self.ui.treeView.model().itemFromIndex(index)
        motor = node.data().toPyObject()[0]
        if motor:
            #TODO
            print motor

    def setMotorTree(self, motors):
        model = MotorTreeModel(motors)
        self.ui.treeView.setModel(model)
        self.ui.treeView.doubleClicked.connect(self.showMotorProperty)
        self.ui.treeView.customContextMenuRequested.connect(self.onTreeViewContextMenu)
        self.ui.treeView.expandAll()

    def load_motor_settings(self, filename):
        logger.info("Load motor settings {}".format(filename))
        with open(filename) as f:
            motors = yaml.load(f)
            self.motors = motors
            for motor in self.motors:
                saved_motor = {'saved_{}'.format(k): v for k, v in motor.items()}
                motor.update(saved_motor)
            self.setMotorTree(self.motors)
