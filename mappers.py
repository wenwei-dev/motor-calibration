import logging
import math
import pandas as pd
from pau2motors import ParserFactory, MapperFactory

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
        self.parser = ParserFactory.build(
            motor_entry["pau"]["parser"])
        self.mapper = MapperFactory.build(
            motor_entry["pau"]["function"], motor_entry)

    def map(self, msg):
        coeff = self.parser.get_coeff(msg)
        angle = self.mapper.map(coeff)
        angle = self._saturated(angle)
        pos = self.angle2pulse(angle)
        return pos

class TrainedMapper(BaseMapper):

    def __init__(self, motor_entry):
        super(TrainedMapper, self).__init__(motor_entry)

    def set_model(self, model):
        self.model = model
        self.params_df = pd.read_csv(self.model, index_col=0)

    def map(self, msg):
        coeff = msg['m_coeffs'][self.params_df.index[:-1]]
        param_num = len(coeff)
        x = self.params_df[self.motor_entry['name']]
        sum = x[:param_num]*coeff + x[-1]
        angle = sum.sum()
        pos = self.angle2pulse(angle)
        return pos

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
