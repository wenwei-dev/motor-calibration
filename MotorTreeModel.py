from PyQt4 import QtCore
from PyQt4 import QtGui
import os
import logging
from MotorController import MotorController
import threading
import subprocess

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

    def query_device_serial(self, device):
        output = subprocess.check_output(['udevadm', 'info', '-q', 'property', '-n', device])
        for line in output.splitlines():
            if line.startswith('ID_SERIAL_SHORT'):
                serial_id = line.split('=')[1]
                return serial_id

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
                serial_id = self.query_device_serial(device)
                name = os.path.split(device)[-1]
                prop_name = name
                if serial_id:
                    prop_name = '{} ({})'.format(name, serial_id)
                node = QtGui.QStandardItem(prop_name)
                node.setEditable(False)
                node.setData(QtCore.QVariant((device,)))
                node.setToolTip(device)
                self.devices.appendRow(node)
                logger.info("Added new device {}".format(device))
                if os.path.basename(device) == 'dynamixel':
                    try:
                        controller = MotorController(str(device))
                        self.app.motor_controllers[name] = controller
                        logger.info("Added controller {}".format(controller))
                    except Exception as ex:
                        logger.error(ex)
                else:
                    try:
                        controller = MotorController(str(device), ids=range(24))
                        self.app.motor_controllers[name] = controller
                        logger.info("Added controller {}".format(controller))
                    except Exception as ex:
                        logger.error(ex)

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self.header[section]
