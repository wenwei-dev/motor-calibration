import threading
import time
import logging
import traceback
from PyQt4 import QtCore
from PyQt4 import QtGui
from ui.motoreditor import Ui_Form

logger = logging.getLogger(__name__)

class MotorValueEditor(QtGui.QWidget):
    def __init__(self, parent, motor):
        super(MotorValueEditor, self).__init__(parent)
        self.motor = motor
        self.app = QtGui.QApplication.instance()

        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.ui.motorValueDoubleSpinBox.valueChanged.connect(self.spinValueChanged)
        self.ui.motorValueSlider.valueChanged.connect(self.sliderValueChanged)
        self.ui.setInitButton.clicked.connect(self.setInitValue)
        self.ui.setMaxButton.clicked.connect(self.setMaxValue)
        self.ui.setMinButton.clicked.connect(self.setMinValue)

        self.active = False
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
                        motor_id = self.motor['motor_id']
                        position = controller.getPosition(motor_id)
                        self.ui.motorValueSlider.setMotorPosition(position)
                        self.ui.motorValueSlider.setValue(int(position*4))
                        logger.info("Get motor {}({}) position {}".format(self.motor['name'], motor_id, position))
                    time.sleep(0.05)
                except Exception as ex:
                    logger.error(traceback.format_exc())
            else:
                time.sleep(0.2)

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
                logger.info("Set motor {}({}) position {}".format(self.motor['name'], motor_id, value))

    def getValue(self):
        return self.ui.motorValueDoubleSpinBox.value()

    def setInitValue(self):
        if self.motor is not None:
            self.motor['init'] = self.getValue()

    def setMaxValue(self):
        if self.motor is not None:
            self.motor['max'] = self.getValue()

    def setMinValue(self):
        if self.motor is not None:
            self.motor['min'] = self.getValue()

    def setActive(self, active):
        self.active = active

    def delete(self):
        self.stopped = True
