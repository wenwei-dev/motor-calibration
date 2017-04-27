from PyQt4 import QtCore
from PyQt4 import QtGui
import os
import logging
from MotorController import MotorController

logger = logging.getLogger(__name__)

class MotorTreeModel(QtGui.QStandardItemModel):

    def __init__(self):
        super(MotorTreeModel, self).__init__()
        self.root = self.invisibleRootItem()
        self.header = ['Motor', 'Device']
        self.devices = QtGui.QStandardItem('Devices')
        self.devices.setEditable(False)
        self.pololu = QtGui.QStandardItem('Pololu Motors')
        self.pololu.setEditable(False)
        self.dynamixel = QtGui.QStandardItem('Dynamixel Motors')
        self.dynamixel.setEditable(False)
        self.root.appendRow(self.devices)
        self.root.appendRow(self.pololu)
        self.root.appendRow(self.dynamixel)
        self.app = QtGui.QApplication.instance()

        self.root.model().rowsInserted.connect(self.dataInserted)

    def dataInserted(self, parent, start, end):
        node = self.root.model().itemFromIndex(parent)
        if node.text() == 'Devices':
            for row in range(start, end+1):
                node = self.devices.child(row)
                device = node.data().toPyObject()[0]
                if device in self.app.motor_controllers:
                    logger.info("Device {} is already added".format(device))
                else:
                    try:
                        controller = MotorController(str(device))
                        self.app.motor_controllers[device] = controller
                        logger.info("Added controller {}".format(device))
                    except Exception as ex:
                        logger.error(ex)

    def addMotors(self, motors):
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

    def updateDevices(self, devices):
        current_devices = []

        # remove old devices
        for row in reversed(range(self.devices.rowCount())):
            node = self.devices.child(row)
            device = node.data().toPyObject()[0]
            if device not in devices:
                self.devices.removeRow(row)
                logger.info("Removed device {}".format(device))
                if device in self.app.motor_controllers:
                    self.app.motor_controllers[device].active = False
                    del self.app.motor_controllers[device]
                    logger.warn("Removed controller {}".format(device))
            else:
                current_devices.append(device)

        # add new devices
        for device in devices:
            if device in current_devices:
                continue
            name = os.path.split(device)[-1]
            node = QtGui.QStandardItem(name)
            node.setEditable(False)
            node.setData(QtCore.QVariant((device,)))
            node.setToolTip(device)
            self.devices.appendRow(node)
            logger.info("Added new device {}".format(device))

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self.header[section]
