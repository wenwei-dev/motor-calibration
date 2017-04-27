from pololu.motors import Maestro
import threading
import logging
import time
import os

logger = logging.getLogger(__name__)

class ChannelInfo(object):
    def __init__(self, id):
        self.id = id
        self.position = None
        self.speed = None
        self.acceleration = None
        self.target = None

class MotorController(object):

    def __init__(self, device):
        self.device = device
        if 'ttyACM' in os.path.basename(os.readlink(self.device)):
            self.hardware = 'pololu'
        elif 'dynamixel' in os.path.basename(self.device):
            self.hardware = 'dynamixel'
        else:
            self.hardware = 'unknown'
        self.controller = None
        self.channels = {}
        for i in range(24):
            self.channels[i] = ChannelInfo(i)
        self.poll_job = threading.Thread(target=self.poll)
        self.poll_job.daemon = True
        self.poll_job.start()

    def init_device(self):
        if self.controller is None:
            try:
                if self.hardware == 'pololu':
                    self.controller = Maestro(self.device)
                    logger.info("Pololu controller {} is initialized".format(self.device))
            except Exception as ex:
                self.controller = None
                logger.error(ex)

    def poll(self):
        while True:
            self.init_device()
            if self.controller is not None:
                for i in range(24):
                    try:
                        self.channels[i].position = self.controller.getPosition(i)/4.0
                    except Exception as ex:
                        logger.error(ex)
                    logger.debug('Device: {}, ID: {}, Position: {}'.format(
                        self.device, i, self.channels[i].position))
            time.sleep(0.1)

    def setTarget(self, id, value):
        try:
            self.controller.setTarget(id, int(value*4))
        except Exception as ex:
            logger.error(ex)

    def setSpeed(self, id, value):
        try:
            self.controller.setSpeed(id, int(value))
        except Exception as ex:
            logger.error(ex)

    def setAcceleration(self, id, value):
        try:
            self.controller.setAcceleration(id, int(value))
        except Exception as ex:
            logger.error(ex)

    def getPosition(self, id):
        return self.channels[id].position

