from scipy.optimize import minimize
import pandas as pd
import numpy as np
import os
import yaml
import logging
import traceback
from mappers import DefaultMapper, TrainedMapper
from configs import Configs
import glob

#ALL_SHAPEKEYS = 'brow_center_DN,brow_center_UP,brow_inner_DN.L,brow_inner_DN.R,brow_inner_UP.L,brow_inner_UP.R,brow_outer_DN.L,brow_outer_DN.R,brow_outer_UP.L,brow_outer_up.R,eye-blink.LO.L,eye-blink.LO.R,eye-blink.UP.L,eye-blink.UP.R,eye-flare.LO.L,eye-flare.LO.R,eye-flare.UP.L,eye-flare.UP.R,eyes-look.dn,eyes-look.up,jaw,lip-DN.C.DN,lip-DN.C.UP,lip-DN.L.DN,lip-DN.L.UP,lip-DN.R.DN,lip-JAW.DN,lip-UP.C.DN,lip-UP.C.UP,lip-UP.L.DN,lip-UP.L.UP,lip-UP.R.DN,lip-UP.R.UP,lip.DN.R.UP,lips-frown.L,lips-frown.R,lips-narrow.L,lips-narrow.R,lips-smile.L,lips-smile.R,lips-wide.L,lips-wide.R,sneer.L,sneer.R,wince.L,wince.R'.split(',')
#ALL_SHAPEKEYS = 'brow_center_DN,brow_center_UP,brow_inner_DN.L,brow_inner_DN.R,brow_inner_UP.L,brow_inner_UP.R,brow_outer_DN.L,brow_outer_DN.R,brow_outer_UP.L,brow_outer_up.R,eye-blink.LO.L,eye-blink.LO.R,eye-blink.UP.L,eye-blink.UP.R,eye-flare.LO.L,eye-flare.LO.R,eye-flare.UP.L,eye-flare.UP.R,eyes-look.dn,eyes-look.up,jaw,lip-DN.C.DN,lip-DN.C.UP,lip-DN.L.DN,lip-DN.L.UP,lip-DN.R.DN,lip-JAW.DN,lip-UP.C.DN,lip-UP.C.UP,lip-UP.L.DN,lip-UP.L.UP,lip-UP.R.DN,lip-UP.R.UP,lip-DN.R.UP,lips-frown.L,lips-frown.R,lips-narrow.L,lips-narrow.R,lips-smile.L,lips-smile.R,lips-wide.L,lips-wide.R,sneer.L,sneer.R,wince.L,wince.R'.split(',') # lip.DN.R.UP -> lip-DN.R.UP
ALL_SHAPEKEYS = 'brow_center_DN,brow_center_UP,brow_inner_DN.L,brow_inner_DN.R,brow_inner_UP.L,brow_inner_UP.R,brow_outer_DN.L,brow_outer_DN.R,brow_outer_UP.L,brow_outer_UP.R,eye-blink.LO.L,eye-blink.LO.R,eye-blink.UP.L,eye-blink.UP.R,eye-flare.LO.L,eye-flare.LO.R,eye-flare.UP.L,eye-flare.UP.R,eyes-look.dn,eyes-look.up,jaw,lip-DN.C.DN,lip-DN.C.UP,lip-DN.L.DN,lip-DN.L.UP,lip-DN.R.DN,lip-JAW.DN,lip-UP.C.DN,lip-UP.C.UP,lip-UP.L.DN,lip-UP.L.UP,lip-UP.R.DN,lip-UP.R.UP,lip-DN.R.UP,lips-frown.L,lips-frown.R,lips-narrow.L,lips-narrow.R,lips-smile.L,lips-smile.R,lips-wide.L,lips-wide.R,sneer.L,sneer.R,wince.L,wince.R'.split(',') # lip.DN.R.UP -> lip-DN.R.UP

#brow_outer_up.R->brow_outer_UP.R

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
        print mse
        return mse

    bounds = [(-1, 1)]*(param_num+1)

    nan_data = targets.isnull()
    targets = targets[nan_data==False]
    shapekey_values = shapekey_values[nan_data==False]
    if shapekey_values.shape[0] == 0 or targets.shape[0] == 0:
        raise Exception('No data to train')
    res = minimize(
        fun, [0.001]*param_num+[0], args=(shapekey_values, targets),
        method='L-BFGS-B', tol=1e-15, options={'disp': False}, bounds=bounds)
    return res

def run(motor_config_file, pau_data_file, targets_file, model_file):
    pau_values = pd.read_csv(pau_data_file)
    targets = pd.read_csv(targets_file)

    with open(motor_config_file) as f:
        motor_configs = yaml.load(f)

    params_df = pd.DataFrame(index=ALL_SHAPEKEYS+['Const'])
    motor_names = targets.columns.tolist()
    for motor_name in motor_names:
        try:
            motor = [motor for motor in motor_configs if motor['name'] == motor_name][0]
        except Exception as ex:
            logger.warn('Motor is not found in configs'.format(motor_name))
            continue

        motor_targets = targets[motor['name']]
        norm_targets = (motor_targets - motor['init'])/(motor['max'] - motor['min'])

        try:
            res = find_params(pau_values[ALL_SHAPEKEYS], norm_targets)
            params_df[motor_name] = res.x
            plot_params(motor, {"frames": pau_values}, params_df, {"frames": targets})
        except Exception as ex:
            logger.warn(ex)
            logger.warn(traceback.format_exc())
            continue
    params_df.to_csv(model_file)

def plot(motor_config_file, pau_data_file, targets_file, model_file):
    pau_values = pd.read_csv(pau_data_file)
    targets = pd.read_csv(targets_file)
    params_df = pd.read_csv(model_file)

    with open(motor_config_file) as f:
        motor_configs = yaml.load(f)

    motor_names = targets.columns.tolist()
    for motor_name in motor_names:
        try:
            motor = [motor for motor in motor_configs if motor['name'] == motor_name][0]
        except Exception as ex:
            logger.warn('Motor is not found in configs'.format(motor_name))
            continue

        try:
            plot_params(motor, {"frames": pau_values}, params_df, {"frames": targets})
        except Exception as ex:
            logger.warn(ex)
            logger.warn(traceback.format_exc())
            continue

def trainMotor(motor, targets, frames):
    try:
        motor_name = str(motor['name'])
        targets = targets[motor_name]
        norm_targets = (targets - motor['init'])/(motor['max'] - motor['min'])
        pau_values = frames[ALL_SHAPEKEYS]
        res = find_params(pau_values, norm_targets)
        if res.success:
            logger.info("Training {} Success, {}".format(motor_name, res.message))
        else:
            logger.warn("Trainig {} Fail, {}".format(motor_name, res.message))
        return res.x
    except Exception as ex:
        logger.error('Train motor {} error, {}'.format(motor['name'], ex))
        return None

def plot_params(motor, frames, model_df, targets):
    motor_name = str(motor['name'])
    import matplotlib.pyplot as plt
    motor_configs = Configs()
    motor_entry = motor_configs.parseMotors([motor])
    motor_entry = motor_configs.motors[0]
    try:
        default_mapper = DefaultMapper(motor_entry)
        trained_mapper = TrainedMapper(motor_entry)
    except Exception as ex:
        logger.error("Can't create mapper, motor {}".format(motor_name))
        return False

    num_figs = len(frames.keys())
    fig, axarr = plt.subplots(num_figs, figsize=(12, 4*num_figs))
    plt.suptitle('Motor Name {}'.format(motor_name))
    if not hasattr(axarr, '__iter__'):
        axarr = [axarr]
    count = 0

    x = model_df.get(motor_name)
    if x is None:
        logger.error("No model for {}".format(motor_name))
        return False
    x = x.tolist()
    for name, shapekey_values in frames.iteritems():
        logger.debug("Plotting fig {}".format(name))
        name = str(name)
        ax = axarr[count]

        param_num = shapekey_values.shape[1]
        row_num = shapekey_values.shape[0]

        default_values = pd.Series(np.nan, index=np.arange(row_num))
        trained_values = pd.Series(np.nan, index=np.arange(row_num))

        for row, m_coeffs in shapekey_values.iterrows():
            try:
                default_value = default_mapper.map(m_coeffs)
                trained_value = trained_mapper._map(m_coeffs[ALL_SHAPEKEYS], x)
            except Exception as ex:
                logger.error(ex)
                logger.error(traceback.format_exc())
                continue
            default_values.set_value(row, default_value)
            trained_values.set_value(row, trained_value)

        target_values = targets[name][motor_name]
        target_values = target_values.dropna()
        trained_values = trained_values.dropna()
        default_values = default_values.dropna()

        ax.plot(default_values.index, default_values, 'go', label='original evaluates', alpha=0.6, ms=3)
        ax.plot(trained_values.index, trained_values, 'bo', label='optimized evaluates', alpha=0.6, ms=3)
        ax.plot(target_values.index, target_values, 'ro', label='targets', alpha=0.6, ms=6)
        ax.vlines(target_values.index, [0], target_values, linestyles='dotted')
        ax.legend(loc='best', fancybox=True, framealpha=0.5)
        if not target_values.empty:
            ax.set_xticks(target_values.index)
            ax.set_xticklabels(target_values.index, rotation='vertical')
        [t.set_rotation(90) for t in ax.xaxis.get_ticklabels()]
        ax.set_xlim(trained_values.index.min()-10, trained_values.index.max()+10)
        if not default_values.empty and not trained_values.empty:
            ax.set_ylim(min(default_values.min(), trained_values.min())-100,
                        max(default_values.max(), trained_values.max())+100)

        error = target_values-trained_values
        mse = (error**2).sum()/error.shape[0]
        ax.set_xlabel('{} MSE: {}'.format(os.path.splitext(name)[0], mse))
        ax.set_ylabel('Motor Value')
        count += 1

    fig_fname = '{}.png'.format(os.path.join(FIG_DIR, motor_name))
    if not os.path.isdir(os.path.dirname(fig_fname)):
        os.makedirs(os.path.dirname(fig_fname))
    fig.tight_layout()
    fig.subplots_adjust(top=0.94)
    fig.savefig(fig_fname)
    plt.close()
    logger.info("Saved fig to {}".format(fig_fname))
    return True

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-m, --motor-config-file', dest='motor_config_file', required=True)
    parser.add_argument('-s, --shapekey-frame-file', dest='shapekey_frame_file', required=True)
    parser.add_argument('-t, --targets-file', dest='targets_file', required=True)
    parser.add_argument('-o, --output-model-file', dest='model_file', required=True)
    parser.add_argument('--plot', dest='plot', action='store_true')
    options = parser.parse_args()

    if os.path.isdir(options.shapekey_frame_file):
        options.shapekey_frame_file = glob.glob('{}/*.csv'.format(options.shapekey_frame_file))

    if os.path.isdir(options.targets_file):
        options.targets_file = glob.glob('{}/*.csv'.format(options.targets_file))

    if options.plot:
        plot(options.motor_config_file, options.shapekey_frame_file, options.targets_file, options.model_file)
    else:
        run(options.motor_config_file, options.shapekey_frame_file, options.targets_file, options.model_file)
