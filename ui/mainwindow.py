# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/mainwindow.ui'
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

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(800, 588)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.horizontalLayout = QtGui.QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.frame = QtGui.QFrame(self.centralwidget)
        self.frame.setFrameShape(QtGui.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtGui.QFrame.Raised)
        self.frame.setObjectName(_fromUtf8("frame"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.frame)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.saveButton = QtGui.QPushButton(self.frame)
        self.saveButton.setObjectName(_fromUtf8("saveButton"))
        self.horizontalLayout_2.addWidget(self.saveButton)
        self.neutralButton = QtGui.QPushButton(self.frame)
        self.neutralButton.setObjectName(_fromUtf8("neutralButton"))
        self.horizontalLayout_2.addWidget(self.neutralButton)
        self.resetButton = QtGui.QPushButton(self.frame)
        self.resetButton.setObjectName(_fromUtf8("resetButton"))
        self.horizontalLayout_2.addWidget(self.resetButton)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.verticalLayout_2.addLayout(self.horizontalLayout_2)
        self.tableView = QtGui.QTableView(self.frame)
        self.tableView.setLineWidth(0)
        self.tableView.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tableView.setShowGrid(True)
        self.tableView.setGridStyle(QtCore.Qt.NoPen)
        self.tableView.setSortingEnabled(True)
        self.tableView.setObjectName(_fromUtf8("tableView"))
        self.verticalLayout_2.addWidget(self.tableView)
        self.motorPropertyWidget = QtGui.QWidget(self.frame)
        self.motorPropertyWidget.setObjectName(_fromUtf8("motorPropertyWidget"))
        self.gridLayout_2 = QtGui.QGridLayout(self.motorPropertyWidget)
        self.gridLayout_2.setMargin(0)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.comboBox = QtGui.QComboBox(self.motorPropertyWidget)
        self.comboBox.setObjectName(_fromUtf8("comboBox"))
        self.gridLayout_2.addWidget(self.comboBox, 3, 1, 1, 1)
        self.label_10 = QtGui.QLabel(self.motorPropertyWidget)
        self.label_10.setObjectName(_fromUtf8("label_10"))
        self.gridLayout_2.addWidget(self.label_10, 3, 0, 1, 1)
        self.label_8 = QtGui.QLabel(self.motorPropertyWidget)
        self.label_8.setObjectName(_fromUtf8("label_8"))
        self.gridLayout_2.addWidget(self.label_8, 1, 0, 1, 1)
        self.doubleSpinBox_4 = QtGui.QDoubleSpinBox(self.motorPropertyWidget)
        self.doubleSpinBox_4.setObjectName(_fromUtf8("doubleSpinBox_4"))
        self.gridLayout_2.addWidget(self.doubleSpinBox_4, 0, 1, 1, 1)
        self.label_7 = QtGui.QLabel(self.motorPropertyWidget)
        self.label_7.setObjectName(_fromUtf8("label_7"))
        self.gridLayout_2.addWidget(self.label_7, 0, 0, 1, 1)
        self.label_9 = QtGui.QLabel(self.motorPropertyWidget)
        self.label_9.setObjectName(_fromUtf8("label_9"))
        self.gridLayout_2.addWidget(self.label_9, 2, 0, 1, 1)
        self.lineEdit_4 = QtGui.QLineEdit(self.motorPropertyWidget)
        self.lineEdit_4.setObjectName(_fromUtf8("lineEdit_4"))
        self.gridLayout_2.addWidget(self.lineEdit_4, 2, 1, 1, 1)
        self.doubleSpinBox = QtGui.QDoubleSpinBox(self.motorPropertyWidget)
        self.doubleSpinBox.setObjectName(_fromUtf8("doubleSpinBox"))
        self.gridLayout_2.addWidget(self.doubleSpinBox, 1, 1, 1, 1)
        self.label_11 = QtGui.QLabel(self.motorPropertyWidget)
        self.label_11.setObjectName(_fromUtf8("label_11"))
        self.gridLayout_2.addWidget(self.label_11, 4, 0, 1, 1)
        self.comboBox_2 = QtGui.QComboBox(self.motorPropertyWidget)
        self.comboBox_2.setObjectName(_fromUtf8("comboBox_2"))
        self.gridLayout_2.addWidget(self.comboBox_2, 4, 1, 1, 1)
        self.verticalLayout_2.addWidget(self.motorPropertyWidget)
        self.horizontalLayout.addWidget(self.frame)
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)
        self.dockWidget = QtGui.QDockWidget(MainWindow)
        self.dockWidget.setObjectName(_fromUtf8("dockWidget"))
        self.dockWidgetContents = QtGui.QWidget()
        self.dockWidgetContents.setObjectName(_fromUtf8("dockWidgetContents"))
        self.verticalLayout = QtGui.QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout.setMargin(0)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.treeView = QtGui.QTreeView(self.dockWidgetContents)
        self.treeView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.treeView.setAlternatingRowColors(True)
        self.treeView.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.treeView.setAnimated(True)
        self.treeView.setObjectName(_fromUtf8("treeView"))
        self.verticalLayout.addWidget(self.treeView)
        self.dockWidget.setWidget(self.dockWidgetContents)
        MainWindow.addDockWidget(QtCore.Qt.DockWidgetArea(1), self.dockWidget)
        self.toolBar = QtGui.QToolBar(MainWindow)
        self.toolBar.setObjectName(_fromUtf8("toolBar"))
        MainWindow.addToolBar(QtCore.Qt.TopToolBarArea, self.toolBar)
        self.actionLoad_motor_settings = QtGui.QAction(MainWindow)
        self.actionLoad_motor_settings.setObjectName(_fromUtf8("actionLoad_motor_settings"))
        self.actionExit = QtGui.QAction(MainWindow)
        self.actionExit.setObjectName(_fromUtf8("actionExit"))
        self.actionEditMotors = QtGui.QAction(MainWindow)
        self.actionEditMotors.setObjectName(_fromUtf8("actionEditMotors"))
        self.toolBar.addAction(self.actionLoad_motor_settings)
        self.toolBar.addAction(self.actionExit)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "ServoController", None))
        self.saveButton.setText(_translate("MainWindow", "Save", None))
        self.neutralButton.setText(_translate("MainWindow", "Neutral", None))
        self.resetButton.setText(_translate("MainWindow", "Reset", None))
        self.label_10.setText(_translate("MainWindow", "Function", None))
        self.label_8.setText(_translate("MainWindow", "Accerlation", None))
        self.label_7.setText(_translate("MainWindow", "Speed", None))
        self.label_9.setText(_translate("MainWindow", "Group", None))
        self.label_11.setText(_translate("MainWindow", "Parser", None))
        self.toolBar.setWindowTitle(_translate("MainWindow", "toolBar", None))
        self.actionLoad_motor_settings.setText(_translate("MainWindow", "Load motor settings...", None))
        self.actionExit.setText(_translate("MainWindow", "Exit", None))
        self.actionEditMotors.setText(_translate("MainWindow", "Edit Motors", None))
        self.actionEditMotors.setToolTip(_translate("MainWindow", "Edit Motors", None))
