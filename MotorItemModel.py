from PyQt4 import QtCore
from PyQt4 import QtGui
from ui.motoreditor import Ui_Form
from pololu.motors import Maestro
import threading
import time
import os
import logging
import traceback

logger = logging.getLogger(__name__)

class MotorValueEditor(QtGui.QWidget):
    def __init__(self, parent, model, row):
        super(MotorValueEditor, self).__init__(parent)
        self.model = model
        self.row = row
        self.motor = self.model.motors[self.row]
        self.app = QtGui.QApplication.instance()

        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.ui.motorValueDoubleSpinBox.valueChanged.connect(self.spinValueChanged)
        self.ui.motorValueSlider.valueChanged.connect(self.sliderValueChanged)
        self.ui.setInitButton.clicked.connect(self.setInitValue)
        self.ui.setMaxButton.clicked.connect(self.setMaxValue)
        self.ui.setMinButton.clicked.connect(self.setMinValue)

        self.active = True
        self.stopped = False
        self.polljob = threading.Thread(target=self.poll)
        self.polljob.daemon = True
        self.polljob.start()

        self.destroyed.connect(self.delete)

    def get_controller(self):
        device = str(self.motor['device'])
        if device in self.app.motor_controllers:
            controller = self.app.motor_controllers[device]
            return controller
        else:
            logger.error("Can't get controller {}".format(self.app.motor_controllers))

    def sliderValueChanged(self, value):
        value = value/4
        if value > self.motor['max']:
            logger.warn("Motor value is greater than maximum")
            return
        elif value < self.motor['min']:
            logger.warn("Motor value is lower than minimum")
            return
        self.ui.motorValueDoubleSpinBox.setValue(value)
        self.setMotorTarget(value)

    def spinValueChanged(self, value):
        if value > self.motor['max']:
            logger.warn("Motor value is greater than maximum")
            return
        elif value < self.motor['min']:
            logger.warn("Motor value is lower than minimum")
            return
        self.ui.motorValueSlider.setValue(int(value*4))
        self.setMotorTarget(value)

    def poll(self):
        while not self.stopped:
            if self.active:
                try:
                    controller = self.get_controller()
                    if controller is not None:
                        position = controller.getPosition(self.motor['motor_id'])
                        self.ui.motorValueSlider.setMotorPosition(position)
                        self.ui.motorValueSlider.setValue(int(position*4))
                        logger.debug("Get motor {} position {}".format(self.motor['name'], position))
                    time.sleep(0.05)
                except Exception as ex:
                    logger.error(traceback.format_exc())

    def setMotorTarget(self, value):
        if self.ui.enableCheckBox.isChecked():
            if value > self.motor['max']:
                logger.warn("Motor value is greater than maximum")
                return
            elif value < self.motor['min']:
                logger.warn("Motor value is lower than minimum")
                return
            controller = self.get_controller()
            if controller is not None:
                motor_id = self.motor['motor_id']
                controller.setAcceleration(motor_id, 0)
                controller.setSpeed(motor_id, int(self.motor['speed']))
                controller.setTarget(motor_id, int(value*4))
                logger.info("Set motor {} position {}".format(self.motor['name'], value))

    def getValue(self):
        return self.ui.motorValueDoubleSpinBox.value()

    def setInitValue(self):
        index = self.model.createIndex(self.row, self.model.header.index('Init'))
        self.model.setData(index, self.getValue(), QtCore.Qt.EditRole)

    def setMaxValue(self):
        index = self.model.createIndex(self.row, self.model.header.index('Max'))
        self.model.setData(index, self.getValue(), QtCore.Qt.EditRole)

    def setMinValue(self):
        index = self.model.createIndex(self.row, self.model.header.index('Min'))
        value = self.getValue()
        self.model.setData(index, self.getValue(), QtCore.Qt.EditRole)

    
    def delete(self):
        self.stopped = True

class MotorValueDelegate(QtGui.QItemDelegate):

    def __init__(self, model):
        super(MotorValueDelegate, self).__init__()
        self.model = model

    def createEditor(self, parent, option, index):
        editor = MotorValueEditor(parent, self.model, index.row())
        return editor

    def setEditorData(self, editor, index):
        motor = self.model.motors[index.row()]
        value = self.model.motors[index.row()]['init']
        editor.ui.motorValueDoubleSpinBox.setValue(value)

    def setModelData(self, editor, model, index):
        logger.info("Set Model Data")

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

class MotorItemModel(QtCore.QAbstractTableModel):

    def __init__(self):
        super(MotorItemModel, self).__init__()
        self.motors = []
        self.fields = ['name', 'device', 'motor_id', 'init', 'min', 'max']
        self.header = ['Name', 'Device', 'MotorID', 'Init', 'Min', 'Max', 'Editor']

    def addMotor(self, motor):
        self.motors.append(motor)

    def rowCount(self, parent):
        return len(self.motors)

    def columnCount(self, parent):
        return len(self.header)

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self.header[section]

    def data(self, index, role):
        col = index.column()
        if col >= len(self.fields):
            return
        field = self.fields[col]
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            motor = self.motors[index.row()]
            return motor.get(field, 'None')
        elif role == QtCore.Qt.BackgroundRole:
            motor = self.motors[index.row()]
            if motor.get('saved_{}'.format(field)) != motor.get(field):
                bg = QtGui.QBrush(QtCore.Qt.yellow)
                return bg

    def flags(self, index):
        if not index.isValid(): return
        return super(MotorItemModel, self).flags(index) | QtCore.Qt.ItemIsEditable

    def setData(self, index, data, role):
        col = index.column()
        if col >= len(self.fields):
            return False
        field = self.fields[col]
        if index.isValid() and role == QtCore.Qt.EditRole:
            motor = self.motors[index.row()]
            if isinstance(data, QtCore.QVariant):
                data = data.toPyObject()
            motor[field] = data
            return True
        else:
            return False
