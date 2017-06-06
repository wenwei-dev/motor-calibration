from pololu.motors import Maestro
from dynamixel_driver import dynamixel_io
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

    def __init__(self, device, ids=[]):
        self.device = device
        if 'ttyACM' in os.path.basename(os.readlink(self.device)):
            self.hardware = 'pololu'
        elif 'dynamixel' in os.path.basename(self.device):
            self.hardware = 'dynamixel'
        else:
            raise ValueError("Device {} is unknown".format(device))
        self.controller = None
        self.channels = {}

        self.active = True

        self.poll_job = threading.Thread(target=self.poll)
        self.poll_job.daemon = True
        self.poll_job.start()

        for i in ids:
            self.channels[i] = ChannelInfo(i)
        if len(ids) == 0:
            self.discover_job = threading.Thread(
                target=self.discover_dynamixel_motors, args=(1, 50))
            self.discover_job.daemon = True
            self.discover_job.start()

    def init_device(self):
        if self.controller is None:
            try:
                if self.hardware == 'pololu':
                    self.controller = Maestro(self.device, readTimeout=0.05)
                    logger.info("Pololu controller {} is initialized".format(self.device))
                elif self.hardware == 'dynamixel':
                    self.controller = dynamixel_io.DynamixelIO(self.device, 1000000)
                else:
                    logger.info("Unknown device {}".format(self.device))
            except Exception as ex:
                self.controller = None
                logger.error(traceback.format_exc())

    def poll(self):
        while self.active:
            self.init_device()
            if self.controller is not None:
                if self.hardware == 'pololu':
                    for channel in self.channels.values():
                        try:
                            channel.position = self.controller.getPosition(channel.id)/4.0
                            channel.valid = True
                        except IndexError:
                            channel.valid = False
                        except Exception as ex:
                            channel.valid = False
                            logger.error(traceback.format_exc())
                        logger.debug('Device: {}, ID: {}, Position: {}'.format(
                            self.device, channel.id, channel.position))
                elif self.hardware == 'dynamixel':
                    for channel in self.channels.values():
                        try:
                            channel.position = self.controller.get_position(channel.id)
                            channel.valid = True
                        except IndexError:
                            channel.valid = False
                        except dynamixel_io.DroppedPacketError:
                            channel.valid = False
                        except Exception as ex:
                            channel.valid = False
                            logger.error(traceback.format_exc())
                        logger.info('Device: {}, ID: {}, Position: {}'.format(
                            self.device, channel.id, channel.position))
            time.sleep(0.05)

    def setTarget(self, id, value):
        try:
            if self.hardware == 'pololu':
                self.controller.setTarget(id, value)
            elif self.hardware == 'dynamixel':
                self.controller.set_position(id, value)
        except Exception as ex:
            logger.error(traceback.format_exc())

    def setSpeed(self, id, value):
        try:
            if self.hardware == 'pololu':
                self.controller.setSpeed(id, value)
            elif self.hardware == 'dynamixel':
                self.controller.set_speed(id, value)
        except Exception as ex:
            logger.error(traceback.format_exc())

    def setAcceleration(self, id, value):
        try:
            if self.hardware == 'pololu':
                self.controller.setAcceleration(id, value)
            elif self.hardware == 'dynamixel':
                logger.warn("Dynamixel doesn't support acceleration")
        except Exception as ex:
            logger.error(traceback.format_exc())

    def getPosition(self, id):
        return self.channels[id].position

    def discover_dynamixel_motors(self, min_motor_id, max_motor_id):
        while self.active:
            if self.hardware != 'dynamixel':
                break
            for i in range(min_motor_id, max_motor_id+1):
                try:
                    response = self.controller.ping(i)
                    if response:
                        self.channels[i] = ChannelInfo(i)
                except Exception as ex:
                    continue
            time.sleep(1)

    def __repr__(self):
        return "<MotorController {}>".format(self.device)
