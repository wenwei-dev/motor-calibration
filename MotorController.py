from pololu.motors import Maestro
import threading
import logging
import time

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
                self.controller = Maestro(self.device)
            except Exception as ex:
                self.controller = None
                logger.error(ex)

    def poll(self):
        while True:
            self.init_device()
            if self.controller is not None:
                for i in range(24):
                    self.channels[i].position = self.controller.getPosition(i)/4
                    logger.info('Device: {}, ID: {}, Position: {}'.format(
                        self.device, i, self.channels[i].position))
            time.sleep(0.1)

    def setTarget(self, id, value):
        self.controller.setTarget(id, value)

    def getPosition(self, id):
        return self.channels[id].position

    def setSpeed(self, id, value):
        self.controller.setSpeed(id, value)

    def setAcceleration(self, id, value):
        self.controller.setAcceleration(id, value)

