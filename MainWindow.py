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
from ui.figwindow import Ui_Dialog
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
from train import trainMotor, plot_params, create_model, FIG_DIR
from functools import partial
import shutil

logger = logging.getLogger(__name__)
CWD = os.path.abspath(os.path.dirname(__name__))
DATA_DIR = os.path.join(CWD, 'data')
TARGET_DIR = os.path.join(DATA_DIR, 'targets')

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
        self.ui.savedMotorValueTableWidget.customContextMenuRequested.connect(
            self.onSavedMotorValueTableWidgetContextMenu)
        self.ui.savedMotorValueTableWidget.itemDoubleClicked.connect(self.showPlot)
        self.ui.motorConfigTableWidget.cellChanged.connect(self.cellChanged)
        self.ui.resetSavedMotorValuesButton.clicked.connect(self.resetSavedMotorValues)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.updateView)
        self.timer.start(200)

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

        self.training = False
        self.frames = {}
        self.frames_df = None
        self.frame_filename = os.path.join(DATA_DIR, 'shapekey-frames.csv')
        self.targets = {}
        self.model_df = create_model()
        self.model_file = os.path.join(DATA_DIR, 'model.csv')
        if os.path.isfile(self.model_file):
            self.model_df = pd.read_csv(self.model_file, index_col=0)
            logger.info("Load model file {}".format(self.model_file))

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
        self.ui.plotButton.clicked.connect(self.plot)

        self.load_motor_settings(os.path.join(DATA_DIR, 'motors_settings.yaml'))

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
        self.ui.saveMotorValuesButton.setEnabled(state!=QtCore.Qt.Unchecked)
        if state!=QtCore.Qt.Unchecked:
            self.playPAU(self.ui.frameSlider.value())

    def init_menu(self):
        self.treeMenu = QtGui.QMenu(self.ui.treeView)
        self.treeMenu.addAction(self.ui.actionEditMotors)
        self.savedMotorValueMenu = QtGui.QMenu(self.ui.savedMotorValueTableWidget)
        self.savedMotorValueMenu.addAction(self.ui.actionClearMotorValues)
        self.ui.actionEditMotors.triggered.connect(self.editMotors)
        self.ui.actionClearMotorValues.triggered.connect(self.clearMotorValues)

    def init_action(self):
        self.ui.saveButton.clicked.connect(self.saveMotors)
        self.ui.resetButton.clicked.connect(self.resetMotors)
        self.ui.neutralButton.clicked.connect(self.neutralMotors)
        self.ui.loadFrameButton.clicked.connect(self.load_frame_dialog)
        self.ui.shapekeyComboBox.currentIndexChanged.connect(self.load_frame)

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
        dialog = QtGui.QFileDialog(self,
            directory=os.path.join(CWD, 'data'), filter='*.csv')
        dialog.setFileMode(QtGui.QFileDialog.ExistingFiles)
        dialog.show()
        dialog.filesSelected.connect(self.load_frames)

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
            global_point = self.ui.treeView.viewport().mapToGlobal(point)
            self.treeMenu.exec_(global_point)

    def onSavedMotorValueTableWidgetContextMenu(self, point):
        global_point = self.ui.savedMotorValueTableWidget.viewport().mapToGlobal(point)
        self.savedMotorValueMenu.exec_(global_point)

    def showPlot(self, item):
        motor = self.ui.savedMotorValueTableWidget.item(item.row(), 0)
        fig_file = os.path.join(FIG_DIR, '{}.png'.format(motor.text()))
        fig = QtGui.QPixmap(fig_file)
        dialog = QtGui.QDialog(self)
        ui = Ui_Dialog()
        ui.setupUi(dialog)
        dialog.ui = ui
        dialog.setModal(False)
        if os.path.isfile(fig_file):
            dialog.ui.figLabel.setPixmap(fig)
        else:
            dialog.ui.figLabel.setText("No fig")
        dialog.show()

    def load_motor_settings(self, filename):
        self.filename = filename
        logger.info("Load motor settings {}".format(filename))
        with open(filename) as f:
            motors = yaml.load(f)
            for motor in motors:
                topic = motor.get('topic')
                if not topic:
                    if motor['hardware'] == 'dynamixel':
                        motor['device'] = 'dynamixel'
                else:
                    motor['device'] = topic
                saved_motor = {'saved_{}'.format(k): v for k, v in motor.items()}
                motor.update(saved_motor)
            self.app.motors = motors
            self.tree_model.removeAllMotors()
            self.tree_model.addMotors(motors)
            self.ui.treeView.expandAll()

            for col in reversed(range(self.ui.motorMonitorTableWidget.columnCount())):
                self.ui.motorMonitorTableWidget.removeColumn(col)
            self.ui.motorMonitorTableWidget.setRowCount(len(motors))
            self.ui.motorMonitorTableWidget.setColumnCount(3)
            self.ui.motorMonitorTableWidget.setHorizontalHeaderLabels('Motor Name,Current,Target'.split(','))
            for row, motor in enumerate(self.app.motors):
                key_item = QtGui.QTableWidgetItem(motor['name'])
                self.ui.motorMonitorTableWidget.setItem(row, 0, key_item)
                current_item = QtGui.QTableWidgetItem()
                current_item.setData(QtCore.Qt.DisplayRole, -1)
                self.ui.motorMonitorTableWidget.setItem(row, 1, current_item)
                target_item = QtGui.QTableWidgetItem()
                target_item.setData(QtCore.Qt.DisplayRole, -1)
                self.ui.motorMonitorTableWidget.setItem(row, 2, target_item)

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
        for row in range(self.ui.motorValueTableWidget.rowCount()):
            widget = self.ui.motorValueTableWidget.cellWidget(row, 2)
            widget.ui.motorValueSlider.update()

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
                    channel = controller.getChannelInfo(int(motor['motor_id']))
                    if channel is not None:
                        motor['current_pos'] = channel.position
                        motor['current_target_pos'] = channel.target_position
            time.sleep(0.1)

    def showMotorValues(self):
        while True:
            for motor in self.app.motors:
                item = self.ui.motorMonitorTableWidget.findItems(
                    motor['name'], QtCore.Qt.MatchExactly)
                current = motor.get('current_pos')
                target = motor.get('current_target_pos')
                if current is not None and item is not None:
                    try:
                        motor_item = item[0]
                        row = motor_item.row()
                        current_item = self.ui.motorMonitorTableWidget.item(row, 1)
                        current_item.setData(QtCore.Qt.DisplayRole, current)
                        target_item = self.ui.motorMonitorTableWidget.item(row, 2)
                        target_item.setData(QtCore.Qt.DisplayRole, target)
                    except Exception as ex:
                        logger.error("Updating motor current position error, {}".format(ex))
            time.sleep(0.1)

    def closeEvent(self, event):
        os.killpg(self.blender_proc.pid, 2)

    def load_frames(self, filenames):
        self.frames = {}
        self.ui.shapekeyComboBox.clear()
        for filename in filenames:
            filename = str(filename)
            df = pd.read_csv(filename)
            if df.shape[1] != len(SHAPE_KEYS):
                logger.error("Frame data dimision is incorrect, filename {}".format(filename))
                continue

            frame_key = os.path.basename(filename)
            self.frames[frame_key] = df

            if not os.path.isdir(TARGET_DIR):
                os.makedirs(TARGET_DIR)

            target_filename = os.path.join(TARGET_DIR, frame_key)
            if not os.path.isfile(target_filename):
                names = [str(motor['name']) for motor in self.app.motors]
                if not names:
                    logger.error("No motors loaded")
                    return
                n_frames = df.shape[0]
                target_df = pd.DataFrame(
                    np.nan, index=np.arange(n_frames), columns=names)
                target_df.to_csv(target_filename, index=False)
                logger.info("Create motor target file {}".format(target_filename))
            else:
                target_df = pd.read_csv(target_filename)
                logger.warn("Read existing motor target file {}".format(
                    target_filename))
            self.targets[frame_key] = target_df
            self.ui.shapekeyComboBox.addItem(frame_key)

        self.ui.shapekeyComboBox.setCurrentIndex(0)

    def load_frame(self, index):
            name = str(self.ui.shapekeyComboBox.itemText(index))
            frame_df = self.frames.get(name)
            if frame_df is not None and frame_df.shape[0] > 0:
                self.ui.frameSlider.setEnabled(True)
                self.ui.frameSlider.setMinimum(0)
                self.ui.frameSlider.setMaximum(frame_df.shape[0]-1)
                self.ui.frameSpinBox.setEnabled(True)
                self.ui.frameSpinBox.setMinimum(0)
                self.ui.frameSpinBox.setMaximum(frame_df.shape[0]-1)
                self.ui.frameSlider.setValue(0)
                self.playPAU(self.ui.frameSlider.value())

    def playPAU(self, frame):
        logger.info("Play PAU frame {}".format(frame))
        name = str(self.ui.shapekeyComboBox.currentText())
        frame_df = self.frames.get(name)
        if frame_df is not None and frame < frame_df.shape[0]:
            m_coeffs = frame_df.iloc[frame]

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
                    target = self.targets[name].iloc[frame][motor_name]
                    target = str(target)
                except Exception as ex:
                    logger.warn("Can't get target, {}".format(ex))
                    logger.warn(traceback.format_exc())
                    target = "nan"
                value_item = self.ui.savedMotorValueTableWidget.item(row, 1)
                value_item.setText(target)

            if self.motor_configs is not None:
                for row, motor in enumerate(self.motor_configs.motors):
                    item = self.ui.motorValueTableWidget.findItems(
                        motor['name'], QtCore.Qt.MatchExactly)
                    if not item:
                        continue

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
                        logger.debug("Create mapper for motor {}, error {}".format(motor['name'], ex))
                        logger.debug(traceback.format_exc())
                    if mapper is not None:
                        try:
                            value = mapper.map(m_coeffs)
                            if hasattr(value, 'item'): # convert numpy float to python native float
                                value = value.item()
                        except Exception as ex:
                            logger.info("Calculate mapper value for motor {}, error {}".format(motor['name'], ex))
                            logger.info(traceback.format_exc())
                            value = -1
                    else:
                        logger.debug("Can't create mapper for {}".format(motor['name']))
                        value = -1

                    # Set motor target
                    motor_item = item[0]
                    row = motor_item.row()
                    value_item = self.ui.motorValueTableWidget.item(row, 1)
                    value_item.setData(QtCore.Qt.DisplayRole, value)
                    widget = self.ui.motorValueTableWidget.cellWidget(row, 2)
                    logger.info("Set motor {} target {}".format(motor['name'], value))
                    if widget and value != -1:
                        widget.ui.motorValueDoubleSpinBox.setValue(value)
                        widget.setMotorTarget(value)
            else:
                logger.error("No motor configs")

    def saveMotorValues(self):
        name = str(self.ui.shapekeyComboBox.currentText())
        frame_df = self.frames.get(name)
        frame = self.ui.frameSlider.value()
        if frame_df is not None and frame < frame_df.shape[0]:
            motor_positions = [motor.get('current_target_pos', np.nan) for motor in self.app.motors]
            target_df = self.targets[name]
            target_filename = os.path.join(TARGET_DIR, name)
            target_df.iloc[frame] = motor_positions
            target_df.to_csv(target_filename, index=False)
            logger.info("Update motor target file {}".format(target_filename))

            # Update Saved motor value
            for row, motor in enumerate(self.app.motors):
                motor_name = str(motor['name'])
                key_item = self.ui.savedMotorValueTableWidget.item(row, 0)
                key_item.setText(motor_name)
                try:
                    target = target_df.iloc[frame][motor_name]
                    target = str(target)
                except Exception as ex:
                    logger.warn(ex)
                    target = "nan"
                value_item = self.ui.savedMotorValueTableWidget.item(row, 1)
                value_item.setText(target)

    def trainModel(self):
        if self.frames:
            if os.path.isdir(FIG_DIR):
                shutil.rmtree(FIG_DIR)
            self.training = True
            self.ui.trainButton.setEnabled(not self.training)
            thread = threading.Thread(target=self._trainModel)
            thread.daemon = True
            thread.start()
        else:
            logger.warn("No frame data")

    def _trainModel(self):
        pool = Pool(6)
        keys = self.frames.keys()
        targets = pd.concat([self.targets[name] for name in keys], ignore_index=True)
        frames = pd.concat([self.frames[name] for name in keys], ignore_index=True)

        params = pool.map(
            partial(trainMotor, targets=targets, frames=frames),
            self.app.motors)
        pool.close()
        pool.join()
        model_updated = False
        for motor, x in zip(self.app.motors, params):
            if x is not None:
                motor_name = str(motor['name'])
                self.model_df[motor_name] = x
                model_updated = True
        if model_updated:
            self.model_df.to_csv(self.model_file)
            logger.info("Saved model to {}".format(self.model_file))
        else:
            logger.info("No model is generated")

        logger.info("Training is finished")
        self.training = False
        self.ui.trainButton.setEnabled(not self.training)

    def plot(self):
        if self.frames:
            if os.path.isdir(FIG_DIR):
                shutil.rmtree(FIG_DIR)
            self._plot()
        else:
            logger.error("No frame data")

    def _plot(self):
        self.ui.plotButton.setEnabled(False)
        pool = Pool(6)
        results = pool.map(
            partial(plot_params, frames=self.frames, model_df=self.model_df, targets=self.targets),
            self.app.motors)
        pool.close()
        pool.join()
        self.ui.plotButton.setEnabled(True)
        logger.info("Plotting is finished")

    def clearMotorValues(self):
        name = str(self.ui.shapekeyComboBox.currentText())
        frame_df = self.frames.get(name)
        frame = self.ui.frameSlider.value()
        if frame_df is not None and frame < frame_df.shape[0]:
            motor_positions = [np.nan for motor in self.app.motors]
            target_df = self.targets[name]
            target_filename = os.path.join(TARGET_DIR, name)
            target_df.iloc[frame] = motor_positions
            target_df.to_csv(target_filename, index=False)
            logger.info("Update motor target file {}".format(target_filename))

            # Update Saved motor value
            for row, motor in enumerate(self.app.motors):
                motor_name = str(motor['name'])
                key_item = self.ui.savedMotorValueTableWidget.item(row, 0)
                key_item.setText(motor_name)
                try:
                    target = target_df.iloc[frame][motor_name]
                    target = str(target)
                except Exception as ex:
                    logger.warn(ex)
                    target = "nan"
                value_item = self.ui.savedMotorValueTableWidget.item(row, 1)
                value_item.setText(target)

    def resetSavedMotorValues(self):
        motor_names = [str(motor['name']) for motor in self.app.motors]
        for name, frame_df in self.frames.items():
            n_frames = frame_df.shape[0]
            target_filename = os.path.join(TARGET_DIR, name)
            target_df = pd.DataFrame(
                np.nan, index=np.arange(n_frames), columns=motor_names)
            target_df.to_csv(target_filename, index=False)
            logger.info("Update motor target file {}".format(target_filename))
            self.targets[name] = target_df

        for row in range(self.ui.savedMotorValueTableWidget.rowCount()):
            value_item = self.ui.savedMotorValueTableWidget.item(row, 1)
            value_item.setText('nan')
        logger.info("Motor targets are reset")
