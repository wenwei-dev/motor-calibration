from PyQt4 import QtCore, QtGui
import logging

logger = logging.getLogger(__name__)

class MotorValueSlider(QtGui.QSlider):

    def __init__(self, parent):
        super(MotorValueSlider, self).__init__(parent)
        self.motor_position = 0

    def setMotorPosition(self, value):
        self.motor_position = value
        try:
            self.update()
        except Exception as ex:
            logger.error(ex)

    def paintEvent(self, event):
        super(MotorValueSlider, self).paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setPen(QtGui.QColor(255, 0, 0, 200))
        painter.setBrush(QtGui.QBrush(QtGui.QColor(0, 255, 0, 200)))
        x = QtGui.QStyle.sliderPositionFromValue(self.minimum(), self.maximum(), int(self.motor_position*4), self.width())
        y = self.height()/2.0
        center = QtCore.QPointF(x, y)
        painter.drawEllipse(center, 5, 5)
