from PyQt4 import QtCore
from PyQt4 import QtGui
from ui.motoreditor import Ui_Form
import threading
import time
import os
import logging
import traceback

logger = logging.getLogger(__name__)

class MotorValueDelegate(QtGui.QItemDelegate):

    def __init__(self):
        super(MotorValueDelegate, self).__init__()
        self.model = None
        self.editors = {}

    def set_model(self, model):
        self.model = model

    def createEditor(self, parent, option, index):
        row = index.row()
        motor = self.model.motors[row]
        motor_key = '{}_{}'.format(motor['motor_id'], motor['device'])
        if motor_key in self.editors:
            editor = self.editors[motor_key]
        else:
            editor = MotorValueEditor(parent, self.model, index.row())
            self.editors[motor_key] = editor
        logger.info("Editor ID {}".format(id(editor)))
        editor.setActive(True)
        return editor

    def setEditorData(self, editor, index):
        motor = self.model.motors[index.row()]
        value = self.model.motors[index.row()]['init']
        editor.ui.motorValueDoubleSpinBox.setValue(value)

    def setModelData(self, editor, model, index):
        logger.info("Set Model Data")

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

    def destroyEditor(self, editor, index):
        editor.setActive(False)

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
