from PyQt4 import QtCore, QtGui

class MotorValueSlider(QtGui.QSlider):

    def __init__(self, parent):
        super(MotorValueSlider, self).__init__(parent)
        self.motor_position = 0

    def setMotorPosition(self, value):
        self.motor_position = value

    def paintEvent(self, event):
        super(MotorValueSlider, self).paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setPen(QtGui.QColor(0, 255, 0, 128))
        x = QtGui.QStyle.sliderPositionFromValue(self.minimum(), self.maximum(), self.motor_position, self.width())
        y = self.height()/2
        painter.drawText(x, y, '*')
