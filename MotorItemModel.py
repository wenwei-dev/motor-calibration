from PyQt4 import QtCore
from PyQt4 import QtGui
from ui.motoreditor import Ui_Form
import copy

class MotorValueEditor(QtGui.QWidget):
    def __init__(self, parent, model, row):
        super(MotorValueEditor, self).__init__(parent)
        self.model = model
        self.row = row
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.ui.motorValueSpinBox.valueChanged.connect(self.spinValueChanged)
        self.ui.motorValueSlider.valueChanged.connect(self.sliderValueChanged)
        self.ui.setInitButton.clicked.connect(self.setInitValue)
        self.ui.setMaxButton.clicked.connect(self.setMaxValue)
        self.ui.setMinButton.clicked.connect(self.setMinValue)

    def sliderValueChanged(self, value):
        self.setValue(value)

    def spinValueChanged(self, value):
        self.setValue(value)

    def setValue(self, value):
        self.ui.motorValueSpinBox.setValue(value)
        self.ui.motorValueSlider.setValue(value)

    def getValue(self):
        return self.ui.motorValueSpinBox.value()

    def setInitValue(self):
        index = self.model.createIndex(self.row, self.model.header.index('Init'))
        self.model.setData(index, QtCore.QVariant(self.getValue()), QtCore.Qt.EditRole)

    def setMaxValue(self):
        index = self.model.createIndex(self.row, self.model.header.index('Max'))
        self.model.setData(index, QtCore.QVariant(self.getValue()), QtCore.Qt.EditRole)

    def setMinValue(self):
        index = self.model.createIndex(self.row, self.model.header.index('Min'))
        self.model.setData(index, QtCore.QVariant(self.getValue()), QtCore.Qt.EditRole)

class MotorValueDelegate(QtGui.QItemDelegate):

    def __init__(self, model):
        super(MotorValueDelegate, self).__init__()
        self.model = model

    def createEditor(self, parent, option, index):
        editor = MotorValueEditor(parent, self.model, index.row())
        return editor

    def setEditorData(self, editor, index):
        value = self.model.motors[index.row()]['init']
        editor.setValue(value)

    def setModelData(self, editor, model, index):
        print "setModelData"
        print editor.ui.getValue()

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class MotorItemModel(QtCore.QAbstractTableModel):

    def __init__(self, motors):
        super(MotorItemModel, self).__init__()
        self.motors = motors
        self.original_motors = copy.deepcopy(motors)
        self.fields = ['name', 'motor_id', 'init', 'min', 'max']
        self.header = ['Name', 'MotorID', 'Init', 'Min', 'Max', 'Editor']

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
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            motor = self.motors[index.row()]
            return '{}'.format(motor[self.fields[col]])
        elif role == QtCore.Qt.BackgroundRole:
            motor = self.motors[index.row()]
            original_motor = self.original_motors[index.row()]
            field = self.fields[col]
            if str(original_motor[field]) != str(motor[field]):
                bg = QtGui.QBrush(QtCore.Qt.yellow)
                return bg
        else:
            pass

    def flags(self, index):
        if not index.isValid(): return
        return super(MotorItemModel, self).flags(index) | QtCore.Qt.ItemIsEditable

    def setData(self, index, data, role):
        col = index.column()
        if col >= len(self.fields):
            return False
        if index.isValid() and role == QtCore.Qt.EditRole:
            motor = self.motors[index.row()]
            if str(motor[self.fields[index.column()]]) != data.toString():
                motor[self.fields[index.column()]] = data.toString()
            return True
        else:
            return False

if __name__ == '__main__':
    import sys
    app = QtGui.QApplication(sys.argv)
    editor = MotorValueEditor()
    editor.show()
    sys.exit(app.exec_())
