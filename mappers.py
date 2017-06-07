import logging
import math
from pau2motors import ParserFactory, MapperFactory

logger = logging.getLogger(__name__)

class DefaultMapper:

    def __init__(self, motor_entry):

        binding_obj = motor_entry["pau"]

        self.parser = ParserFactory.build(
        binding_obj["parser"]
        )
        self.mapper = MapperFactory.build(
        binding_obj["function"],
        motor_entry
        )
        self.motor_entry = motor_entry

    def map(self, msg):
        coeff = self.parser.get_coeff(msg)
        angle = self.mapper.map(coeff)
        pos = self.angle2pulse(angle)
        return pos

    def angle2pulse(self, angle):
        rmin = self.motor_entry['min']
        rmax = self.motor_entry['max']
        pmin = self.motor_entry['pulse_min']
        pmax = self.motor_entry['pulse_max']
        pos = (angle-rmin)/(rmax-rmin)*(pmax-pmin)+pmin
        return pos

    def _saturated(self, angle):
        return min(max(angle, self.motor_entry['min']), self.motor_entry['max'])  

if __name__ == '__main__':
    import pandas as pd
    import yaml
    from configs import Configs
    logging.getLogger().setLevel(logging.INFO)
    df = pd.read_csv('data/shkey_frame_data.csv')
    with open('data/motors_settings.yaml') as f:
        motor_entries = yaml.load(f)
        configs = Configs()
        configs.parseMotors(motor_entries)
        for motor in configs.motors:
            try:
                mapping = DefaultMapper(motor)
                angle = mapping.map({'m_coeffs':df.loc[20]})
                print angle, mapping.angle2pulse(angle), motor['name']
            except Exception as ex:
                print motor['name'], ex