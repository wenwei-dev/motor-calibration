import os
import logging
import yaml
import threading
from multiprocessing.dummy import Pool as ThreadPool
from multiprocessing import Pool
import time
from PyQt4 import QtCore
from PyQt4 import QtGui
from ui.mainwindow import Ui_MainWindow
from MotorTreeModel import MotorTreeModel
from MotorValueEditor import MotorValueEditor
from collections import OrderedDict
import subprocess
from blender import SHAPE_KEYS
import pandas as pd
import numpy as np
from configs import Configs
from mappers import DefaultMapper, TrainedMapper
import traceback
from train import ALL_SHAPEKEYS, find_params, trainMotor
from functools import partial

logger = logging.getLogger(__name__)

class MainWindow(QtGui.QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.init_menu()
        self.init_action()
        self.ui.actionExit.triggered.connect(self.close)
        self.ui.actionLoad_Motor_Settings.triggered.connect(self.load_motor_settings_dialog)
        self.ui.actionSave_Motor_Settings.triggered.connect(self.save_motor_settings_dialog)
        self.tree_model = MotorTreeModel()
        self.ui.treeView.setModel(self.tree_model)
        self.ui.treeView.selectionModel().selectionChanged.connect(self.selectMotor)
        self.ui.treeView.customContextMenuRequested.connect(self.onTreeViewContextMenu)
        self.ui.motorConfigTableWidget.cellChanged.connect(self.cellChanged)

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

        self.blender_proc = subprocess.Popen(['python', 'blender.py'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                preexec_fn=os.setsid)
        self.blender_thread = threading.Thread(
            target=self.readPAU, args=(self.blender_proc.stdout,))
        self.blender_thread.daemon = True
        self.blender_thread.start()
        self.ui.pauTableWidget.setRowCount(len(SHAPE_KEYS))
        self.ui.pauTableWidget.setColumnCount(2)
        self.ui.pauValueTableWidget.setRowCount(len(SHAPE_KEYS))
        self.ui.pauValueTableWidget.setColumnCount(2)
        self.ui.frameSlider.valueChanged.connect(self.playPAU)

        self.frames = None
        self.frame_filename = None
        self.motor_value_filename = None
        self.saved_motor_values_df = None
        self.model_df = pd.DataFrame(index=ALL_SHAPEKEYS+['Const'])
        self.model_file = '/tmp/mapping_model.csv'
        self.training = False

        self.motor_value_thread = threading.Thread(target=self.readMotorValues)
        self.motor_value_thread.daemon = True
        self.motor_value_thread.start()
        self.show_motor_value_thread = threading.Thread(target=self.showMotorValues)
        self.show_motor_value_thread.daemon = True
        self.show_motor_value_thread.start()

        self.motor_configs = None

        self.playMotorCheckState = QtCore.Qt.Unchecked
        self.calibMotorCheckState = QtCore.Qt.Unchecked
        self.configMotorCheckState = QtCore.Qt.Unchecked
        self.ui.enableConfigMotorsCheckBox.stateChanged.connect(self.enableConfigMotors)
        self.ui.enablePlayMotorsCheckBox.stateChanged.connect(self.enablePlayMotors)
        self.button_group = QtGui.QButtonGroup(self)
        self.button_group.addButton(self.ui.defaultMapperButton)
        self.button_group.addButton(self.ui.trainedMapperButton)
        self.ui.saveMotorValuesButton.clicked.connect(self.saveMotorValues)
        self.ui.trainButton.clicked.connect(self.trainModel)

        self.load_motor_settings('/home/wenwei/workspace/hansonrobotics/motor-controller/motors_settings.yaml')
        self.load_frames('/home/wenwei/workspace/hansonrobotics/motor-controller/data/shkey_frame_data.csv')

    def enableConfigMotors(self, state):
        self.configMotorCheckState = state
        header = self.motor_header.keys()
        for row in range(self.ui.motorConfigTableWidget.rowCount()):
            widget = self.ui.motorConfigTableWidget.cellWidget(row, len(header))
            if widget:
                widget.ui.enableCheckBox.setCheckState(self.configMotorCheckState)

    def enablePlayMotors(self, state):
        self.playMotorCheckState = state
        for row in range(self.ui.motorValueTableWidget.rowCount()):
            widget = self.ui.motorValueTableWidget.cellWidget(row, 2)
            if widget:
                widget.ui.enableCheckBox.setCheckState(self.playMotorCheckState)

    def init_menu(self):
        self.treeMenu = QtGui.QMenu(self.ui.treeView)
        self.treeMenu.addAction(self.ui.actionEditMotors)
        self.ui.actionEditMotors.triggered.connect(self.editMotors)

    def init_action(self):
        self.ui.saveButton.clicked.connect(self.saveMotors)
        self.ui.resetButton.clicked.connect(self.resetMotors)
        self.ui.neutralButton.clicked.connect(self.neutralMotors)
        self.ui.loadFrameButton.clicked.connect(self.load_frame_dialog)

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

    def load_frame_dialog(self):
        dialog = QtGui.QFileDialog(self, filter='*.csv')
        dialog.show()
        dialog.fileSelected.connect(self.load_frames)

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
        columnCount = self.ui.motorConfigTableWidget.columnCount()
        widgets = []
        for row in range(self.ui.motorConfigTableWidget.rowCount()):
            widget = self.ui.motorConfigTableWidget.cellWidget(row, columnCount-1)
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
        for col in reversed(range(self.ui.motorConfigTableWidget.columnCount())):
            self.ui.motorConfigTableWidget.removeColumn(col)

        header = self.motor_header.keys()
        self.ui.motorConfigTableWidget.setRowCount(len(motors))
        self.ui.motorConfigTableWidget.setColumnCount(len(header)+1)
        self.ui.motorConfigTableWidget.setColumnWidth(len(header), 800)
        self.ui.motorConfigTableWidget.setHorizontalHeaderLabels(header+['Editor'])

        for row, motor in enumerate(motors):
            for col, key in enumerate(self.motor_header.values()):
                item = QtGui.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, motor[key])
                self.ui.motorConfigTableWidget.setItem(row, col, item)

            widget = MotorValueEditor(self.ui.motorConfigTableWidget, motor, row)
            self.ui.motorConfigTableWidget.setCellWidget(row, len(header), widget)
            widget.ui.enableCheckBox.setCheckState(self.configMotorCheckState)
            widget.setVisible(False)
        self.neutralMotors()

        # Update motor value table widget
        for col in reversed(range(self.ui.motorValueTableWidget.columnCount())):
            self.ui.motorValueTableWidget.removeColumn(col)

        self.ui.motorValueTableWidget.setRowCount(len(motors))
        self.ui.motorValueTableWidget.setColumnCount(3)
        self.ui.motorValueTableWidget.setHorizontalHeaderLabels('Motor Name,Target,Editor'.split(','))
        for row, motor in enumerate(motors):
            key_item = QtGui.QTableWidgetItem(motor['name'])
            self.ui.motorValueTableWidget.setItem(row, 0, key_item)
            value_item = QtGui.QTableWidgetItem()
            value_item.setData(QtCore.Qt.DisplayRole, -1)
            self.ui.motorValueTableWidget.setItem(row, 1, value_item)
            widget = MotorValueEditor(self.ui.motorValueTableWidget, motor, row, False)
            self.ui.motorValueTableWidget.setCellWidget(row, 2, widget)
            widget.ui.enableCheckBox.setCheckState(self.playMotorCheckState)
            widget.setVisible(False)

        self.playPAU(self.ui.frameSlider.value())

    def getCurrentMotors(self):
        motors = []
        columnCount = self.ui.motorConfigTableWidget.columnCount()
        for row in range(self.ui.motorConfigTableWidget.rowCount()):
            widget = self.ui.motorConfigTableWidget.cellWidget(row, columnCount-1)
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
                motor['device'] = motor.get('topic')
                saved_motor = {'saved_{}'.format(k): v for k, v in motor.items()}
                motor.update(saved_motor)
            self.app.motors = motors
            self.tree_model.removeAllMotors()
            self.tree_model.addMotors(motors)
            self.ui.treeView.expandAll()

            for col in reversed(range(self.ui.motorMonitorTableWidget.columnCount())):
                self.ui.motorMonitorTableWidget.removeColumn(col)
            self.ui.motorMonitorTableWidget.setRowCount(len(motors))
            self.ui.motorMonitorTableWidget.setColumnCount(2)
            self.ui.motorMonitorTableWidget.setHorizontalHeaderLabels('Motor Name,Target'.split(','))
            for row, motor in enumerate(self.app.motors):
                key_item = QtGui.QTableWidgetItem(motor['name'])
                self.ui.motorMonitorTableWidget.setItem(row, 0, key_item)
                value_item = QtGui.QTableWidgetItem()
                value_item.setData(QtCore.Qt.DisplayRole, -1)
                self.ui.motorMonitorTableWidget.setItem(row, 1, value_item)

            self.motor_configs = Configs()
            self.motor_configs.parseMotors(motors)

            for col in reversed(range(self.ui.savedMotorValueTableWidget.columnCount())):
                self.ui.savedMotorValueTableWidget.removeColumn(col)
            self.ui.savedMotorValueTableWidget.setRowCount(len(motors))
            self.ui.savedMotorValueTableWidget.setColumnCount(2)
            self.ui.savedMotorValueTableWidget.setHorizontalHeaderLabels('Motor Name,Target'.split(','))
            for row, motor in enumerate(self.app.motors):
                key_item = QtGui.QTableWidgetItem(motor['name'])
                self.ui.savedMotorValueTableWidget.setItem(row, 0, key_item)
                value_item = QtGui.QTableWidgetItem('nan')
                self.ui.savedMotorValueTableWidget.setItem(row, 1, value_item)

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
        item = self.ui.motorConfigTableWidget.item(row, col)
        columnCount = self.ui.motorConfigTableWidget.columnCount()
        editor = self.ui.motorConfigTableWidget.cellWidget(row, columnCount-1)
        if item is not None and editor is not None:
            motor = editor.motor
            motor_attribs = self.motor_header.values()
            motor_attrib = motor_attribs[col]
            data = item.data(QtCore.Qt.EditRole).toPyObject()
            motor[motor_attrib] = data
            logger.info("Update motor {}={}".format(motor_attrib, data))

    def updateView(self):
        columnCount = self.ui.motorConfigTableWidget.columnCount()
        widgets = []
        for row in range(self.ui.motorConfigTableWidget.rowCount()):
            widget = self.ui.motorConfigTableWidget.cellWidget(row, columnCount-1)
            widget.ui.motorValueSlider.update()
            motor = widget.motor
            for col, key in enumerate(self.motor_header.values()):
                item = self.ui.motorConfigTableWidget.item(row, col)
                data = item.data(QtCore.Qt.EditRole).toPyObject()
                if motor['saved_{}'.format(key)] != data:
                    item.setForeground(QtGui.QBrush(QtGui.QColor(65,105,225)))
                else:
                    item.setForeground(QtGui.QBrush(QtGui.QColor(0,0,0)))
        self.ui.motorConfigTableWidget.viewport().update()

    def readPAU(self, f):
        for line in iter(f.readline, ''):
            try:
                coeffs = eval(line)
            except Exception as ex:
                logger.warn("Read PAU error {}".format(ex))
                continue
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

    def readMotorValues(self):
        while True:
            for motor in self.app.motors:
                device = str(motor['device'])
                controller = self.app.motor_controllers.get(device)
                if controller is not None:
                    position = controller.getPosition(motor['motor_id'])
                    motor['current_pos'] = position
            time.sleep(0.1)

    def showMotorValues(self):
        while True:
            for motor in self.app.motors:
                item = self.ui.motorMonitorTableWidget.findItems(
                    motor['name'], QtCore.Qt.MatchExactly)
                position = motor.get('current_pos')
                if position is not None and item is not None:
                    motor_item = item[0]
                    row = motor_item.row()
                    value_item = self.ui.motorMonitorTableWidget.item(row, 1)
                    value_item.setData(QtCore.Qt.DisplayRole, position)
            time.sleep(0.1)

    def closeEvent(self, event):
        os.killpg(self.blender_proc.pid, 2)

    def load_frames(self, filename):
        self.frames = pd.read_csv(filename)
        self.frame_filename = filename
        self.motor_value_filename = '{}-motors.csv'.format(
            os.path.splitext(self.frame_filename)[0])
        self.model_file = '{}-model.csv'.format(
            os.path.splitext(self.frame_filename)[0])

        self.ui.frameSlider.setEnabled(True)
        self.ui.frameSlider.setMinimum(0)
        self.ui.frameSlider.setMaximum(self.frames.shape[0]-1)
        self.ui.frameSpinBox.setEnabled(True)
        self.ui.frameSpinBox.setMinimum(0)
        self.ui.frameSpinBox.setMaximum(self.frames.shape[0]-1)
        if self.frames.shape[1] != len(SHAPE_KEYS):
            logger.error("Frame data dimision is incorrect")
            return

        if not os.path.isfile(self.motor_value_filename):
            names = [motor['name'] for motor in self.app.motors]
            if not names:
                logger.error("No motors loaded")
                return
            total_frames = self.frames.shape[0]
            self.saved_motor_values_df = pd.DataFrame(
                np.nan, index=np.arange(total_frames), columns=names)
            self.saved_motor_values_df.to_csv(self.motor_value_filename, index=False)
            logger.info("Motor target file {}".format(self.motor_value_filename))
        else:
            self.saved_motor_values_df = pd.read_csv(self.motor_value_filename)
            logger.warn("Append to existing motor target file {}".format(
                self.motor_value_filename))

        if self.frames.shape[0] > 0:
            self.ui.frameSlider.setValue(0)
            self.playPAU(self.ui.frameSlider.value())

    def playPAU(self, frame):
        if self.frames is not None and frame < self.frames.shape[0]:
            m_coeffs = self.frames.loc[frame]

            # Update table
            for row, (key, value) in enumerate(m_coeffs.iteritems()):
                key_item = self.ui.pauValueTableWidget.item(row, 0)
                if key_item is None:
                    key_item = QtGui.QTableWidgetItem(key)
                    self.ui.pauValueTableWidget.setItem(row, 0, key_item)
                else:
                    key_item.setText(key)
                value_item = self.ui.pauValueTableWidget.item(row, 1)
                value = value.item()
                if value_item is None:
                    value_item = QtGui.QTableWidgetItem()
                    value_item.setData(QtCore.Qt.DisplayRole, value)
                    self.ui.pauValueTableWidget.setItem(row, 1, value_item)
                else:
                    value_item.setData(QtCore.Qt.DisplayRole, value)

            # Update Saved motor value
            for row, motor in enumerate(self.app.motors):
                motor_name = str(motor['name'])
                key_item = self.ui.savedMotorValueTableWidget.item(row, 0)
                key_item.setText(motor_name)
                try:
                    target = self.saved_motor_values_df.loc[frame][motor_name]
                    target = str(target)
                except Exception as ex:
                    logger.warn(ex)
                    target = "nan"
                value_item = self.ui.savedMotorValueTableWidget.item(row, 1)
                value_item.setText(target)

            if self.motor_configs is not None:
                for row, motor in enumerate(self.motor_configs.motors):
                    mapper = None
                    try:
                        if str(self.button_group.checkedButton().text()) == 'Default Mapper':
                            mapper = DefaultMapper(motor)
                        elif str(self.button_group.checkedButton().text()) == 'Trained Mapper':
                            mapper = TrainedMapper(motor)
                            mapper.set_model(self.model_df)
                        else:
                            logger.error("No motor mapper for {}".format(motor['name']))
                            continue
                    except Exception as ex:
                        logger.debug("Can't initilize mapper for motor {}, error {}".format(motor['name'], ex))
                    if mapper is not None:
                        try:
                            value = mapper.map({'m_coeffs':m_coeffs})
                            value = value.item()
                        except Exception as ex:
                            logger.debug("Motor {} has no key {}".format(motor['name'], ex))
                            value = -1
                    else:
                        value = -1

                    item = self.ui.motorValueTableWidget.findItems(
                        motor['name'], QtCore.Qt.MatchExactly)
                    if item:
                        motor_item = item[0]
                        row = motor_item.row()
                        value_item = self.ui.motorValueTableWidget.item(row, 1)
                        value_item.setData(QtCore.Qt.DisplayRole, value)
                        widget = self.ui.motorValueTableWidget.cellWidget(row, 2)
                        if widget and value != -1:
                            widget.ui.motorValueDoubleSpinBox.setValue(value)
            else:
                logger.error("No motor configs")

    def saveMotorValues(self):
        frame = self.ui.frameSlider.value()
        total_frames = self.frames.shape[0]
        if self.frames is not None and frame < total_frames:
            motor_positions = [motor.get('current_pos', np.nan) for motor in self.app.motors]
            self.saved_motor_values_df.loc[frame] = motor_positions
            self.saved_motor_values_df.to_csv(self.motor_value_filename, index=False)

            # Update Saved motor value
            for row, motor in enumerate(self.app.motors):
                motor_name = str(motor['name'])
                key_item = self.ui.savedMotorValueTableWidget.item(row, 0)
                key_item.setText(motor_name)
                try:
                    target = self.saved_motor_values_df.loc[frame][motor_name]
                    target = str(target)
                except Exception as ex:
                    logger.warn(ex)
                    target = "nan"
                value_item = self.ui.savedMotorValueTableWidget.item(row, 1)
                value_item.setText(target)

    def trainModel(self):
        self.training = True
        self.ui.trainButton.setEnabled(not self.training)
        threading.Thread(target=self._trainModel).start()

    def _trainModel(self):
        pool = Pool(6)
        params = pool.map(
            partial(trainMotor, targets=self.saved_motor_values_df, frames=self.frames),
            self.app.motors)
        pool.close()
        pool.join()
        logger.info("Training is finished")

        for motor, x in zip(self.app.motors, params):
            if x is not None:
                motor_name = str(motor['name'])
                self.model_df[motor_name] = x
        self.model_df.to_csv(self.model_file)
        logger.info("Save model to {}".format(self.model_file))

        self.training = False
        self.ui.trainButton.setEnabled(not self.training)
