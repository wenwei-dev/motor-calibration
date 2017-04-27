import os
import logging
import yaml
import threading
import time
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
        self.ui.motorPropertyWidget.hide()
        self.init_menu()
        self.init_action()
        self.ui.actionExit.triggered.connect(self.close)
        self.ui.actionLoad_Motor_Settings.triggered.connect(self.load_motor_settings_dialog)
        self.ui.actionSave_Motor_Settings.triggered.connect(self.save_motor_settings_dialog)
        self.tree_model = MotorTreeModel()
        self.ui.treeView.setModel(self.tree_model)
        self.ui.treeView.selectionModel().selectionChanged.connect(self.selectMotor)
        self.ui.treeView.customContextMenuRequested.connect(self.onTreeViewContextMenu)

        self.device_monitor_job = threading.Thread(target=self.monitor_devices)
        self.device_monitor_job.daemon = True
        self.device_monitor_job.start()
        self.app = QtGui.QApplication.instance()
        self.app.motors = []
        self.app.motor_controllers = {}
        self.filename = None

    def init_menu(self):
        self.treeMenu = QtGui.QMenu(self.ui.treeView)
        self.treeMenu.addAction(self.ui.actionEditMotors)
        self.ui.actionEditMotors.triggered.connect(self.editMotors)

    def init_action(self):
        self.ui.saveButton.clicked.connect(self.saveMotors)
        self.ui.resetButton.clicked.connect(self.resetMotors)

    def close(self):
        super(MainWindow, self).close()

    def load_motor_settings_dialog(self):
        dialog = QtGui.QFileDialog(self, filter='*.yaml')
        dialog.show()
        dialog.fileSelected.connect(self.load_motor_settings)

    def save_motor_settings_dialog(self):
        dialog = QtGui.QFileDialog(self, filter='*.yaml')
        dialog.show()
        dialog.fileSelected.connect(self.save_motor_settings)

    def saveMotors(self):
        for motor in self.ui.tableView.model().motors:
            for k in motor.keys():
                if not k.startswith('saved_'):
                    k2 = 'saved_{}'.format(k)
                    if k2 not in motor:
                        logger.warn("Motor has no attribute {}".format(k2))
                    else:
                        motor[k2] = motor[k]

    def resetMotors(self):
        for motor in self.ui.tableView.model().motors:
            for k in motor.keys():
                if not k.startswith('saved_'):
                    k2 = 'saved_{}'.format(k)
                    if k2 not in motor:
                        logger.warn("Motor has no attribute {}".format(k2))
                    else:
                        motor[k] = motor[k2]

    def editMotors(self):
        indexes = self.ui.treeView.selectedIndexes()
        motors = []
        for index in indexes:
            node = self.ui.treeView.model().itemFromIndex(index)
            motor = node.data().toPyObject()
            if motor:
                motor = motor[0]
                if isinstance(motor, dict) and 'motor_id' in motor:
                    motors.append(motor)
        self.addMotorsToController(motors)

    def editMotor(self, index):
        node = self.ui.treeView.model().itemFromIndex(index)
        motor = node.data().toPyObject()
        if motor:
            motor = motor[0]
            if isinstance(motor, dict) and 'motor_id' in motor:
                self.addMotorsToController([motor])

    def selectMotor(self, selection):
        self.editMotors()

    def addMotorsToController(self, motors):
        model = MotorItemModel()
        for motor in motors:
            model.addMotor(motor)

        editor_index = model.header.index('Editor')
        delegate = MotorValueDelegate(model)
        old_model = self.ui.tableView.model()
        if old_model:
            for row in range(old_model.rowCount(QtCore.QModelIndex())):
                index = model.createIndex(row, editor_index)
                self.ui.tableView.closePersistentEditor(index)
        self.ui.tableView.setModel(model)
        self.ui.tableView.verticalHeader().hide()
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

    def load_motor_settings(self, filename):
        self.filename = filename
        logger.info("Load motor settings {}".format(filename))
        with open(filename) as f:
            motors = yaml.load(f)
            for motor in motors:
                motor['device'] = '/dev/hr/head/sophia6/{}'.format(motor['topic'])
                saved_motor = {'saved_{}'.format(k): v for k, v in motor.items()}
                motor.update(saved_motor)
            self.app.motors.extend(motors)
            self.tree_model.addMotors(motors)
            self.ui.treeView.expandAll()

    def save_motor_settings(self, filename):
        filename = str(filename)
        if os.path.splitext(filename)[1] != '.yaml':
            filename = filename+'.yaml'
        with open(filename, 'w') as f:
            saved_motors = []
            for motor in self.app.motors:
                saved_motor = {}
                for k, v in motor.items():
                    if k.startswith('saved_'):
                        k2 = k.split('_',1)[1]
                        saved_motor[k2] = motor[k]
                saved_motors.append(saved_motor)
            yaml.dump(saved_motors, f, default_flow_style=False)
            logger.info("Saved to {}".format(filename))

    def monitor_devices(self):
        while True:
            devices = []
            for dirpath, dirnames, filenames in os.walk('/dev/hr'):
                if filenames:
                    for filename  in filenames:
                        filename = os.path.join(dirpath, filename)
                        devices.append(filename)
            self.tree_model.updateDevices(devices)
            time.sleep(0.5)
