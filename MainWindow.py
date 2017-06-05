import os
import logging
import yaml
import threading
from multiprocessing.dummy import Pool as ThreadPool
import time
from PyQt4 import QtCore
from PyQt4 import QtGui
from ui.mainwindow import Ui_MainWindow
from MotorTreeModel import MotorTreeModel
from MotorValueEditor import MotorValueEditor
from collections import OrderedDict
import subprocess
from blender import SHAPE_KEYS

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
        self.ui.tableWidget.cellChanged.connect(self.cellChanged)
        self.blender_proc = subprocess.Popen(['python', 'blender.py'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                preexec_fn=os.setsid)
        self.blender_thread = threading.Thread(
            target=self.readpau, args=(self.blender_proc.stdout,))
        self.blender_thread.daemon = True
        self.blender_thread.start()
        self.ui.pauTableWidget.setRowCount(len(SHAPE_KEYS))
        self.ui.pauTableWidget.setColumnCount(2)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.updateView)
        self.timer.start(300)

        self.motor_header = OrderedDict()
        self.motor_header['Name'] = 'name'
        self.motor_header['Device'] = 'device'
        self.motor_header['Motor ID'] = 'motor_id'
        self.motor_header['Min'] = 'min'
        self.motor_header['Init'] = 'init'
        self.motor_header['Max'] = 'max'

        self.device_monitor_job = threading.Thread(target=self.monitor_devices)
        self.device_monitor_job.daemon = True
        self.device_monitor_job.start()
        self.app = QtGui.QApplication.instance()
        self.app.motors = []
        self.app.motor_controllers = {}
        self.app.motor_header = self.motor_header
        self.filename = None

        self.load_motor_settings('/home/wenwei/workspace/hansonrobotics/motor-controller/motors_settings.yaml')

    def init_menu(self):
        self.treeMenu = QtGui.QMenu(self.ui.treeView)
        self.treeMenu.addAction(self.ui.actionEditMotors)
        self.ui.actionEditMotors.triggered.connect(self.editMotors)

    def init_action(self):
        self.ui.saveButton.clicked.connect(self.saveMotors)
        self.ui.resetButton.clicked.connect(self.resetMotors)
        self.ui.neutralButton.clicked.connect(self.neutralMotors)

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
        for motor in self.getCurrentMotors():
            for k in motor.keys():
                if not k.startswith('saved_'):
                    k2 = 'saved_{}'.format(k)
                    if k2 not in motor:
                        logger.warn("Motor has no attribute {}".format(k2))
                    else:
                        motor[k2] = motor[k]
            logger.info("Saved {}".format(motor['name']))

    def resetMotors(self):
        for motor in self.getCurrentMotors():
            for k in motor.keys():
                if not k.startswith('saved_'):
                    k2 = 'saved_{}'.format(k)
                    if k2 not in motor:
                        logger.warn("Motor has no attribute {}".format(k2))
                    else:
                        motor[k] = motor[k2]
            logger.info("Reset {}".format(motor['name']))

    def neutralMotors(self):
        columnCount = self.ui.tableWidget.columnCount()
        widgets = []
        for row in range(self.ui.tableWidget.rowCount()):
            widget = self.ui.tableWidget.cellWidget(row, columnCount-1)
            widgets.append(widget)

        def update(widget):
            widget.setValue(widget.motor['saved_init'])

        pool = ThreadPool(8)
        pool.map(update, widgets)
        pool.close()
        pool.join()
        logger.info("Set motor to neutral")

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
        for col in reversed(range(self.ui.tableWidget.columnCount())):
            self.ui.tableWidget.removeColumn(col)

        header = self.motor_header.keys()
        self.ui.tableWidget.setRowCount(len(motors))
        self.ui.tableWidget.setColumnCount(len(header)+1)
        self.ui.tableWidget.setColumnWidth(len(header), 800)
        self.ui.tableWidget.setHorizontalHeaderLabels(header+['Editor'])

        for row, motor in enumerate(motors):
            for col, key in enumerate(self.motor_header.values()):
                item = QtGui.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, motor[key])
                self.ui.tableWidget.setItem(row, col, item)
                item = self.ui.tableWidget.item(row, col)

            widget = MotorValueEditor(self.ui.tableWidget, motor, row)
            self.ui.tableWidget.setCellWidget(row, len(header), widget)
            widget.setVisible(False)
        self.neutralMotors()

    def getCurrentMotors(self):
        motors = []
        columnCount = self.ui.tableWidget.columnCount()
        for row in range(self.ui.tableWidget.rowCount()):
            widget = self.ui.tableWidget.cellWidget(row, columnCount-1)
            motors.append(widget.motor)
        return motors

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
                motor['device'] = motor['topic']
                saved_motor = {'saved_{}'.format(k): v for k, v in motor.items()}
                motor.update(saved_motor)
            self.app.motors = motors
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

    def cellChanged(self, row, col):
        item = self.ui.tableWidget.item(row, col)
        columnCount = self.ui.tableWidget.columnCount()
        editor = self.ui.tableWidget.cellWidget(row, columnCount-1)
        if item is not None and editor is not None:
            motor = editor.motor
            motor_attribs = self.motor_header.values()
            motor_attrib = motor_attribs[col]
            data = item.data(QtCore.Qt.EditRole).toPyObject()
            motor[motor_attrib] = data
            logger.info("Update motor {}={}".format(motor_attrib, data))

    def updateView(self):
        columnCount = self.ui.tableWidget.columnCount()
        widgets = []
        for row in range(self.ui.tableWidget.rowCount()):
            widget = self.ui.tableWidget.cellWidget(row, columnCount-1)
            widget.ui.motorValueSlider.update()
            motor = widget.motor
            for col, key in enumerate(self.motor_header.values()):
                item = self.ui.tableWidget.item(row, col)
                data = item.data(QtCore.Qt.EditRole).toPyObject()
                if motor['saved_{}'.format(key)] != data:
                    item.setForeground(QtGui.QBrush(QtGui.QColor(65,105,225)))
                else:
                    item.setForeground(QtGui.QBrush(QtGui.QColor(0,0,0)))
        self.ui.tableWidget.viewport().update()

    def readpau(self, f):
        for line in iter(f.readline, ''):
            coeffs = eval(line)
            for row, (key, value) in enumerate(zip(SHAPE_KEYS, coeffs)):
                key_item = self.ui.pauTableWidget.item(row, 0)
                if key_item is None:
                    key_item = QtGui.QTableWidgetItem(key)
                    self.ui.pauTableWidget.setItem(row, 0, key_item)
                else:
                    key_item.setText(key)
                value_item = self.ui.pauTableWidget.item(row, 1)
                if value_item is None:
                    value_item = QtGui.QTableWidgetItem()
                    value_item.setData(QtCore.Qt.DisplayRole, value)
                    self.ui.pauTableWidget.setItem(row, 1, value_item)
                else:
                    value_item.setData(QtCore.Qt.DisplayRole, value)

    def closeEvent(self, event):
        os.killpg(self.blender_proc.pid, 2)
