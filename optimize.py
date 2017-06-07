from scipy.optimize import minimize
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
import yaml

ALL_SHAPEKEYS = ["brow_center_UP", "brow_center_DN", "brow_inner_UP.L", "brow_inner_DN.L", "brow_inner_UP.R", "brow_inner_DN.R", "brow_outer_UP.L", "brow_outer_DN.L", "brow_outer_UP.R", "brow_outer_DN.R", "eye-flare.UP.L", "eye-blink.UP.L", "eye-flare.UP.R", "eye-blink.UP.R", "eye-blink.LO.L", "eye-flare.LO.L", "eye-blink.LO.R", "eye-flare.LO.R", "wince.L", "wince.R", "sneer.L", "sneer.R", "eyes-look.dn", "eyes-look.up", "lip-UP.C.UP", "lip-UP.C.DN", "lip-UP.L.UP", "lip-UP.L.DN", "lip-UP.R.UP", "lip-UP.R.DN", "lips-smile.L", "lips-smile.R", "lips-wide.L", "lips-narrow.L", "lips-wide.R", "lips-narrow.R", "lip-DN.C.DN", "lip-DN.C.UP", "lip-DN.L.DN", "lip-DN.L.UP", "lip-DN.R.DN", "lip-DN.R.UP", "lips-frown.L", "lips-frown.R", "lip-JAW.DN"]
ALL_MOTOR_NAMES = ["Brow-Outer-L", "Brow-Inner-L", "Brow-Center", "Brow-Inner-R", "Brow-Outer-R", "Upper-Lid-L", "Upper-Lid-R", "Lower-Lid-L", "LowerLid-R", "Sneer-L", "Sneer-R", "Cheek-Squint-L", "Cheek-Squint-R", "Upper-Lip-L", "Upper-Lip-Center", "Upper-Lip-R", "Smile_L", "Smile_R", "EE-R", "Frown_R", "EE-L", "Frown_L", "Lower-Lip-L", "Lower-Lip-Center", "Lower-Lip-R"]

def softmax(x):
    """Compute softmax values for each sets of scores in x."""
    return np.exp(x) / np.sum(np.exp(x), axis=0)

def find_params(motor, shapekey_values, targets):
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

    res = minimize(fun, [0.1]*param_num+[0], args=(shapekey_values, targets), method='L-BFGS-B', tol=1e-15, options={'disp': False}, bounds=bounds)
    return res

def evaluate_params(motor, shapekey_values, x, targets):
    param_num = shapekey_values.shape[1]

    sum = x[:param_num]*shapekey_values + x[-1]
    values = sum.sum(axis=1)
    #values = values*(motor['max'] - motor['min'])+motor['init']

    error = targets-values
    print error
    print 'mse', (error**2).sum()

    fig, ax = plt.subplots()
    ax.plot(range(targets.size), targets, label='target')
    ax.plot(range(values.size), values, label='value')
    ax.legend(loc='lower right')
    fig_fname = '{}.png'.format(os.path.join('figs', motor['name']))
    fig.savefig(fig_fname)
    print "Saved fig to {}".format(fig_fname)
    plt.close()

def run(motor_name, motor_data, pau_values, test_pau_values):
    with open('motors_settings.yaml') as f:
        motor_config = yaml.load(f)
    motor = [motor for motor in motor_config if motor['name'] == motor_name][0]
    targets = motor_data[motor['name']]
    norm_targets = (targets - motor['init'])/(motor['max'] - motor['min'])

    shapekeys = motor['parser_param'].split(';')
    shapekeys = ALL_SHAPEKEYS

    res = find_params(motor, pau_values[shapekeys], norm_targets)
    index = np.argsort(softmax(np.absolute(res.x)))
    names = shapekeys+['Constant']
    print res.x
    print [names[i] for i in index]
    print [res.x[i] for i in index]

    evaluate_params(motor, test_pau_values[shapekeys], res.x, norm_targets)


motor_data = pd.read_csv('motor_data.csv')
pau_values = pd.read_csv('pau_values.csv')
#test_pau_values = pd.read_csv('test_pau_values.csv')
test_pau_values = pd.read_csv('pau_data.csv')
#motor_data = pd.read_csv('motor_data_random.csv')
#pau_values = pd.read_csv('pau_values_random.csv')

for motor_name in ALL_MOTOR_NAMES:
    print motor_name
    run(motor_name, motor_data, pau_values, test_pau_values)
