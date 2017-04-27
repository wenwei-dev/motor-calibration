from pololu.motors import Maestro
import threading
import logging
import time
import os
import traceback

logger = logging.getLogger(__name__)

class ChannelInfo(object):
    def __init__(self, id):
        self.id = id
        self.position = None
        self.speed = None
        self.acceleration = None
        self.target = None
        self.valid = False

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

        self.active = True
        self.poll_job = threading.Thread(target=self.poll)
        self.poll_job.daemon = True
        self.poll_job.start()

    def init_device(self):
        if self.controller is None:
            try:
                if self.hardware == 'pololu':
                    self.controller = Maestro(self.device, readTimeout=0.2)
                    logger.info("Pololu controller {} is initialized".format(self.device))
            except Exception as ex:
                self.controller = None
                logger.error(traceback.format_exc())

    def poll(self):
        while self.active:
            self.init_device()
            if self.controller is not None:
                for i in range(24):
                    try:
                        self.channels[i].position = self.controller.getPosition(i)/4.0
                        self.channels[i].valid = True
                    except IndexError:
                        self.channels[i].valid = False
                    except Exception as ex:
                        self.channels[i].valid = False
                        logger.error(traceback.format_exc())
                    logger.debug('Device: {}, ID: {}, Position: {}'.format(
                        self.device, i, self.channels[i].position))
            time.sleep(0.2)

    def setTarget(self, id, value):
        try:
            self.controller.setTarget(id, value)
        except Exception as ex:
            logger.error(traceback.format_exc())

    def setSpeed(self, id, value):
        try:
            self.controller.setSpeed(id, value)
        except Exception as ex:
            logger.error(traceback.format_exc())

    def setAcceleration(self, id, value):
        try:
            self.controller.setAcceleration(id, value)
        except Exception as ex:
            logger.error(traceback.format_exc())

    def getPosition(self, id):
        return self.channels[id].position

