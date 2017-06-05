import logging
from PyQt4 import QtGui
import sys
sys.path.insert(0, '/opt/hansonrobotics/py2env/lib/python2.7/dist-packages')
sys.path.insert(0, '/opt/hansonrobotics/ros/lib/python2.7/dist-packages')

from MainWindow import MainWindow

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO,
        format='[%(name)s][%(levelname)s] %(asctime)s: %(message)s')
    logger.info("Start")
    app = QtGui.QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.showMaximized()
    sys.exit(app.exec_())
