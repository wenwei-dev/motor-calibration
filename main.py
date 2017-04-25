import logging
from PyQt4 import QtGui

from mainwindow import MainWindow

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    logger.info("Start")
    app = QtGui.QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.showMaximized()
    sys.exit(app.exec_())
