import logging
import math
import pandas as pd
import MapperFactory

logger = logging.getLogger(__name__)

class BaseMapper(object):

    def __init__(self, motor_entry):
        self.motor_entry = motor_entry

    def angle2pulse(self, angle):
        rmin = self.motor_entry['min']
        rmax = self.motor_entry['max']
        pmin = self.motor_entry['pulse_min']
        pmax = self.motor_entry['pulse_max']
        pos = (angle-rmin)/(rmax-rmin)*(pmax-pmin)+pmin
        return pos

    def _saturated(self, angle):
        return min(max(angle, self.motor_entry['min']), self.motor_entry['max'])

class DefaultMapper(BaseMapper):

    def __init__(self, motor_entry):
        super(DefaultMapper, self).__init__(motor_entry)
        self.mapper = MapperFactory.build(
            motor_entry["pau"]["function"], motor_entry)

    def map(self, msg):
        keys = self.motor_entry['pau']['parser']['shapekey'].split(';')
        coeff = msg[keys]
        angle = self.mapper.map(coeff)
        angle = self._saturated(angle)
        pos = self.angle2pulse(angle)
        return pos

class TrainedMapper(BaseMapper):

    def __init__(self, motor_entry):
        super(TrainedMapper, self).__init__(motor_entry)

    def set_model(self, model_df):
        self.model_df = model_df

    def angle2pulse(self, angle):
        pos = angle*(self.motor_entry['pulse_max']-self.motor_entry['pulse_min'])+self.motor_entry['init']
        return pos

    def _map(self, coeff, x):
        param_num = len(coeff)
        sum = x[:param_num]*coeff + x[-1]
        angle = sum.sum()
        pos = self.angle2pulse(angle)
        return pos

    def map(self, msg):
        coeff = msg[self.model_df.index[:-1]]
        x = self.model_df[self.motor_entry['name']]
        return self._map(coeff, x)

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    import pandas as pd
    import yaml
    from configs import Configs
    logging.getLogger().setLevel(logging.INFO)
    df = pd.read_csv('data/shkey_frame_data.csv')
    with open('motors_settings.yaml') as f:
        motor_entries = yaml.load(f)
        configs = Configs()
        configs.parseMotors(motor_entries)
        for motor in configs.motors:
            try:
                mapper = DefaultMapper(motor)
                angle = mapper.map({'m_coeffs':df.loc[20]})
                print angle, motor['name']
            except Exception as ex:
                print 'error', motor['name'], ex

        for motor in configs.motors:
            try:
                mapper = TrainedMapper(motor)
                mapper.set_model('motor_mapping_model.csv')
                angle = mapper.map({'m_coeffs':df.loc[20]})
                print angle, motor['name']
            except Exception as ex:
                print 'error', motor['name'], ex
