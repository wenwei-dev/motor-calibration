from PyQt4 import QtCore
from PyQt4 import QtGui
import os
import logging
from MotorController import MotorController
import threading

logger = logging.getLogger(__name__)

class MotorTreeModel(QtGui.QStandardItemModel):

    def __init__(self):
        super(MotorTreeModel, self).__init__()
        self._lock = threading.RLock()
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
        with self._lock:
            current_devices = []

            # remove old devices
            for row in reversed(range(self.devices.rowCount())):
                node = self.devices.child(row)
                device = node.data().toPyObject()[0]
                name = str(node.text())
                if device not in devices:
                    self.devices.removeRow(row)
                    logger.info("Removed device {}".format(device))
                    if name in self.app.motor_controllers:
                        self.app.motor_controllers[name].active = False
                        del self.app.motor_controllers[name]
                        logger.warn("Removed controller {}:{}".format(name, device))
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
                try:
                    controller = MotorController(str(device))
                    self.app.motor_controllers[name] = controller
                    logger.info("Added controller {}:{}".format(name, device))
                except Exception as ex:
                    logger.error(ex)

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self.header[section]
