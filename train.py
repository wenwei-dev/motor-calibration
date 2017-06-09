import sys
sys.path.insert(0, '/opt/hansonrobotics/py2env/lib/python2.7/dist-packages')
sys.path.insert(0, '/opt/hansonrobotics/ros/lib/python2.7/dist-packages')

from scipy.optimize import minimize
import pandas as pd
import numpy as np
import os
import yaml
import logging
import traceback
from mappers import DefaultMapper, TrainedMapper
from configs import Configs

ALL_SHAPEKEYS = 'brow_center_DN,brow_center_UP,brow_inner_DN.L,brow_inner_DN.R,brow_inner_UP.L,brow_inner_UP.R,brow_outer_DN.L,brow_outer_DN.R,brow_outer_UP.L,brow_outer_up.R,eye-blink.LO.L,eye-blink.LO.R,eye-blink.UP.L,eye-blink.UP.R,eye-flare.LO.L,eye-flare.LO.R,eye-flare.UP.L,eye-flare.UP.R,eyes-look.dn,eyes-look.up,jaw,lip-DN.C.DN,lip-DN.C.UP,lip-DN.L.DN,lip-DN.L.UP,lip-DN.R.DN,lip-JAW.DN,lip-UP.C.DN,lip-UP.C.UP,lip-UP.L.DN,lip-UP.L.UP,lip-UP.R.DN,lip-UP.R.UP,lip.DN.R.UP,lips-frown.L,lips-frown.R,lips-narrow.L,lips-narrow.R,lips-smile.L,lips-smile.R,lips-wide.L,lips-wide.R,sneer.L,sneer.R,wince.L,wince.R'.split(',')

logger = logging.getLogger(__name__)
FIG_DIR = 'figs'

def create_model():
    return pd.DataFrame(index=ALL_SHAPEKEYS+['Const'])

def softmax(x):
    """Compute softmax values for each sets of scores in x."""
    return np.exp(x) / np.sum(np.exp(x), axis=0)

def find_params(shapekey_values, targets):
    param_num = shapekey_values.shape[1]

    def fun(x, shapekey_values, targets):
        '''
            fun = a*x_1 + b*x_2 + c
        '''
        sum = x[:param_num]*shapekey_values + x[-1]
        diff = sum.sum(axis=1)-targets
        mse = (diff**2).sum()
        return mse

    bounds = [(-1, 1)]*(param_num+1)

    nan_data = targets.isnull()
    targets = targets[nan_data==False]
    shapekey_values = shapekey_values[nan_data==False]
    if shapekey_values.shape[0] == 0 or targets.shape[0] == 0:
        raise Exception('No data to train')
    res = minimize(
        fun, [0.1]*param_num+[0], args=(shapekey_values, targets),
        method='L-BFGS-B', tol=1e-15, options={'disp': False}, bounds=bounds)
    return res

def run(motor_config_file, pau_data_file, motor_data_file, model_file):
    pau_values = pd.read_csv(pau_data_file)
    motor_data = pd.read_csv(motor_data_file)

    with open(motor_config_file) as f:
        motor_configs = yaml.load(f)

    params_df = pd.DataFrame(index=ALL_SHAPEKEYS+['Const'])
    motor_names = motor_data.columns.tolist()
    for motor_name in motor_names:
        try:
            motor = [motor for motor in motor_configs if motor['name'] == motor_name][0]
        except Exception as ex:
            logger.warn('Motor is not found in configs'.format(motor_name))
            continue

        targets = motor_data[motor['name']]
        norm_targets = (targets - motor['init'])/(motor['max'] - motor['min'])

        shapekeys = ALL_SHAPEKEYS
        try:
            res = find_params(pau_values[shapekeys], norm_targets)
            params_df[motor_name] = res.x
            plot_params(motor, pau_values[shapekeys], res.x, targets)
        except Exception as ex:
            logger.warn(ex)
            logger.warn(traceback.format_exc())
            continue
    params_df.to_csv(model_file)

def trainMotor(motor, targets, frames):
    motor_name = str(motor['name'])
    targets = targets[motor_name]
    norm_targets = (targets - motor['init'])/(motor['max'] - motor['min'])
    pau_values = frames[ALL_SHAPEKEYS]
    try:
        res = find_params(pau_values, norm_targets)
        if res.success:
            logger.info("Training {} Success, {}".format(motor_name, res.message))
        else:
            logger.warn("Trainig {} Fail, {}".format(motor_name, res.message))
        return res.x
    except Exception as ex:
        pass

def plot_params(motor, shapekey_values, x, targets):
    import matplotlib.pyplot as plt
    motor_configs = Configs()
    motor_entry = motor_configs.parseMotors([motor])
    motor_entry = motor_configs.motors[0]
    param_num = shapekey_values.shape[1]
    row_num = shapekey_values.shape[0]

    default_mapper = DefaultMapper(motor_entry)
    trained_mapper = TrainedMapper(motor_entry)
    default_values = pd.Series(np.nan, index=np.arange(row_num))
    trained_values = pd.Series(np.nan, index=np.arange(row_num))

    for row, m_coeffs in shapekey_values.iterrows():
        try:
            default_value = default_mapper.map(m_coeffs)
            trained_value = trained_mapper._map(m_coeffs, x)
        except Exception as ex:
            continue
        default_values.set_value(row, default_value)
        trained_values.set_value(row, trained_value)

    error = targets-trained_values
    mse = (error**2).sum()

    fig, ax = plt.subplots()
    ax.set_title('Motor Name {}, MSE {}'.format(motor['name'], mse))
    ax.set_xlabel('Frame')
    ax.set_ylabel('Motor Value')
    targets = targets.dropna()
    ax.plot(default_values.index, default_values, 'go', label='original evaluates', alpha=0.6, ms=3)
    ax.plot(trained_values.index, trained_values, 'bo', label='optimized evaluates', alpha=0.6, ms=3)
    ax.plot(targets.index, targets, 'ro', label='targets', alpha=0.6, ms=6)
    ax.vlines(targets.index, [0], targets, linestyles='dotted')
    ax.set_xlim(trained_values.index.min()-10, trained_values.index.max()+10)
    ax.set_ylim(min(default_values.min(), trained_values.min())-100,
                max(default_values.max(), trained_values.max())+100)
    plt.xticks(targets.index, targets.index, rotation='vertical')

    ax.legend(loc='best', fancybox=True, framealpha=0.5)
    fig_fname = '{}.png'.format(os.path.join(FIG_DIR, motor['name']))
    if not os.path.isdir(os.path.dirname(fig_fname)):
        os.makedirs(os.path.dirname(fig_fname))
    fig.savefig(fig_fname)
    plt.close()
    logger.info("Saved fig to {}".format(fig_fname))

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-m, --motor-config-file', dest='motor_config_file', required=True)
    parser.add_argument('-s, --shapekey-frame-file', dest='shapekey_frame_file', required=True)
    parser.add_argument('-d, --motor-data-file', dest='motor_data_file', required=True)
    parser.add_argument('-o, --output-model-file', dest='model_file', required=True)
    options = parser.parse_args()
    run(options.motor_config_file, options.shapekey_frame_file, options.motor_data_file, options.model_file)
