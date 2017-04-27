# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/motoreditor.ui'
#
# Created by: PyQt4 UI code generator 4.12
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName(_fromUtf8("Form"))
        Form.resize(600, 36)
        self.verticalLayout = QtGui.QVBoxLayout(Form)
        self.verticalLayout.setMargin(0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.enableCheckBox = QtGui.QCheckBox(Form)
        self.enableCheckBox.setText(_fromUtf8(""))
        self.enableCheckBox.setObjectName(_fromUtf8("enableCheckBox"))
        self.horizontalLayout.addWidget(self.enableCheckBox)
        self.motorValueSlider = MotorValueSlider(Form)
        self.motorValueSlider.setEnabled(False)
        self.motorValueSlider.setAutoFillBackground(True)
        self.motorValueSlider.setMinimum(800)
        self.motorValueSlider.setMaximum(2500)
        self.motorValueSlider.setOrientation(QtCore.Qt.Horizontal)
        self.motorValueSlider.setTickPosition(QtGui.QSlider.TicksBelow)
        self.motorValueSlider.setTickInterval(100)
        self.motorValueSlider.setObjectName(_fromUtf8("motorValueSlider"))
        self.horizontalLayout.addWidget(self.motorValueSlider)
        self.motorValueSpinBox = QtGui.QSpinBox(Form)
        self.motorValueSpinBox.setEnabled(False)
        self.motorValueSpinBox.setMinimum(800)
        self.motorValueSpinBox.setMaximum(2500)
        self.motorValueSpinBox.setProperty("value", 900)
        self.motorValueSpinBox.setObjectName(_fromUtf8("motorValueSpinBox"))
        self.horizontalLayout.addWidget(self.motorValueSpinBox)
        self.setMinButton = QtGui.QPushButton(Form)
        self.setMinButton.setObjectName(_fromUtf8("setMinButton"))
        self.horizontalLayout.addWidget(self.setMinButton)
        self.setInitButton = QtGui.QPushButton(Form)
        self.setInitButton.setObjectName(_fromUtf8("setInitButton"))
        self.horizontalLayout.addWidget(self.setInitButton)
        self.setMaxButton = QtGui.QPushButton(Form)
        self.setMaxButton.setObjectName(_fromUtf8("setMaxButton"))
        self.horizontalLayout.addWidget(self.setMaxButton)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(_translate("Form", "Form", None))
        Form.setToolTip(_translate("Form", "Enable Motor", None))
        self.enableCheckBox.setWhatsThis(_translate("Form", "Enable Motor", None))
        self.motorValueSlider.setToolTip(_translate("Form", "Slide it to change motor target position", None))
        self.motorValueSpinBox.setToolTip(_translate("Form", "Motor target position", None))
        self.setMinButton.setToolTip(_translate("Form", "Set the current position as mininum position", None))
        self.setMinButton.setText(_translate("Form", "Set Min", None))
        self.setInitButton.setToolTip(_translate("Form", "Set the current position as initial position", None))
        self.setInitButton.setText(_translate("Form", "Set Init", None))
        self.setMaxButton.setToolTip(_translate("Form", "Set the current position as maximum position", None))
        self.setMaxButton.setText(_translate("Form", "Set Max", None))

from motorvalueslider import MotorValueSlider