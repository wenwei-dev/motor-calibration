import pandas as pd
import numpy as np
import os
import yaml

def evaluate(shapekey_values, x):
    param_num = shapekey_values.shape[1]
    sum = x[:param_num]*shapekey_values + x[-1]
    values = sum.sum(axis=1)
    return values

def run(motor_config_file, pau_data_file, model_file):
    params_df = pd.read_csv(model_file, index_col=0)
    pau_values = pd.read_csv(pau_data_file)

    with open(motor_config_file) as f:
        motor_configs = yaml.load(f)

    motor_names = params_df.columns.tolist()
    for motor_name in motor_names:
        try:
            motor = [motor for motor in motor_configs if motor['name'] == motor_name][0]
        except Exception as ex:
            print 'Motor is not found in configs'.format(motor_name)
            continue
        x = params_df[motor_name]
        values = evaluate(pau_values, x)
        values = values*(motor['max']-motor['min'])+motor['init']
        print values

if __name__ == '__main__':
    run('motors_settings.yaml', 'data/shkey_frame_data.csv', 'motor_mapping_model.csv')
