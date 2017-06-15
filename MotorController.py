import sys
sys.path.insert(0, '/opt/hansonrobotics/py2env/lib/python2.7/dist-packages')
sys.path.insert(0, '/opt/hansonrobotics/ros/lib/python2.7/dist-packages')

from pololu.motors import Maestro
from dynamixel_driver import dynamixel_io
import threading
import logging
import time
import os
import traceback
import serial

logger = logging.getLogger(__name__)

class ChannelInfo(object):
    def __init__(self, id):
        self.id = id
        self.position = None
        self.target_position = None
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
                target=self.discover_dynamixel_motors, args=(0, 50))
            self.discover_job.daemon = True
            self.discover_job.start()

    def init_device(self):
        if self.controller is None:
            try:
                if self.hardware == 'pololu':
                    self.controller = Maestro(self.device, readTimeout=0.05, log=logger)
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
                        except serial.SerialException as ex:
                            channel.valid = False
                        except Exception as ex:
                            channel.valid = False
                            logger.error(traceback.format_exc())
                        logger.info('Device: {}, ID: {}, Position: {}'.format(
                            self.device, channel.id, channel.position))
                elif self.hardware == 'dynamixel':
                    for channel in self.channels.values():
                        try:
                            channel.position = self.controller.get_position(channel.id)
                            channel.valid = True
                        except dynamixel_io.ChecksumError:
                            channel.valid = False
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
                if id in self.channels:
                    self.channels[id].target_position = value/4
                    logger.info("Set channel {} target {}".format(id, value/4))
                else:
                    logger.warn("Can't set channel {} target {}".format(id, value/4))
            elif self.hardware == 'dynamixel':
                try:
                    self.controller.set_position(id, value)
                except dynamixel_io.DroppedPacketError as ex:
                    logger.info("Error in setting target for motor {}, {}".format(id, ex))
                if id in self.channels:
                    self.channels[id].target_position = value
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

    def getChannelInfo(self, id):
        if id in self.channels:
            return self.channels[id]
        else:
            logger.info("No such channel {}, device {}, channels {}".format(id, self.device, self.channels.keys()))

    def getPosition(self, id):
        if id in self.channels:
            return self.channels[id].position
        else:
            return -1

    def discover_dynamixel_motors(self, min_motor_id, max_motor_id):
        while self.active:
            if self.hardware != 'dynamixel':
                break
            for i in range(min_motor_id, max_motor_id+1):
                try:
                    response = self.controller.ping(i)
                    if response:
                        if i not in self.channels:
                            self.channels[i] = ChannelInfo(i)
                            logger.info("Found motor id {}".format(i))
                        angle = self.controller.get_angle_limits(i)
                        mode = self.controller.get_drive_mode(i)
                        voltage = self.controller.get_voltage(i)
                        speed = self.controller.get_speed(i)
                        model_number = self.controller.get_model_number(i)
                        firmware_version = self.controller.get_firmware_version(i)
                        #print i, angle, mode, voltage, speed, model_number, firmware_version
                except Exception as ex:
                    continue
            time.sleep(1)

    def enableMotor(self, id, enabled):
        if self.hardware == 'dynamixel':
            retry = 5
            while retry > 0:
                try:
                    response = self.controller.set_torque_enabled(id, enabled)
                    print 'response', response
                    if response:
                        if enabled:
                            logger.info("Enabled torque for motor {}".format(id))
                        else:
                            logger.info("Disabled torque for motor {}".format(id))
                        break
                except dynamixel_io.DroppedPacketError as ex:
                    logger.warn("Error in setting motor torque for motor {}, {}".format(id, ex))
                time.sleep(0.1)
                retry -= 1

    def __repr__(self):
        return "<MotorController {}>".format(self.device)
