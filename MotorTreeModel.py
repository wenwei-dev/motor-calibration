from PyQt4 import QtCore
from PyQt4 import QtGui

class MotorTreeModel(QtGui.QStandardItemModel):

    def __init__(self, motors):
        super(MotorTreeModel, self).__init__()
        self.root = self.invisibleRootItem()
        self.header = ['Motor', 'Device']
        self.pololu = QtGui.QStandardItem('pololu')
        self.pololu.setEditable(False)
        self.dynamixel = QtGui.QStandardItem('dynamixel')
        self.dynamixel.setEditable(False)
        self.root.appendRow(self.pololu)
        self.root.appendRow(self.dynamixel)
        for motor in motors:
            self.addMotor(motor)

    def addMotor(self, motor):
        node = QtGui.QStandardItem(motor['name'])
        node.setEditable(False)
        node.setData(QtCore.QVariant((motor,)))

        if motor['hardware'] == 'pololu':
            self.pololu.appendRow(node)
        elif motor['hardware'] == 'dynamixel':
            self.dynamixel.appendRow(node)

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self.header[section]
