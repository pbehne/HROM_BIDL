import numpy as np
import tensorflow as tf
from dolfin import *
from forward_solve import Fin, get_space
from pandas import read_csv

def generate_five_param(dataset_size, resolution=40):
    V = get_space(resolution)
    dofs = len(V.dofmap().dofs())

    # TODO: Improve this by using mass matrix covariance. Bayesian prior may work well too
    z_s = np.random.uniform(0.1, 1, (dataset_size, 5))
    phi = np.loadtxt('data/basis_five_param.txt',delimiter=",")
    phi = phi[:,0:20]
    solver = Fin(V)
    errors = np.zeros((dataset_size, 1))

    for i in range(dataset_size):
        w, y, A, B, C = solver.forward_five_param(z_s[i,:])
        psi = np.dot(A, phi)
        A_r, B_r, C_r, x_r, y_r = solver.reduced_forward(A, B, C, psi, phi)
        errors[i][0] = y - y_r 

    #  np.savetxt('data/z_s_eval.txt', z_s, delimiter=",")
    #  np.savetxt('data/errors_eval.txt', errors, delimiter=",")
    dataset = tf.data.Dataset.from_tensor_slices((z_s,errors))

    return dataset

def generate_five_param_np(dataset_size, resolution=40):
    V = get_space(resolution)
    z_s = np.random.uniform(0.1, 1, (dataset_size, 5))
    phi = np.loadtxt('data/basis_five_param.txt',delimiter=",")
    phi = phi[:,0:10]
    solver = Fin(V)
    errors = np.zeros((dataset_size, 1))
    y_s = np.zeros((dataset_size, 1))
    y_r_s = np.zeros((dataset_size, 1))

    for i in range(dataset_size):
        w, y, A, B, C = solver.forward_five_param(z_s[i,:])
        y_s[i][0] = y
        psi = np.dot(A, phi)
        A_r, B_r, C_r, x_r, y_r = solver.reduced_forward(A, B, C, psi, phi)
        y_r_s[i][0] = y_r
        errors[i][0] = y - y_r 

    return (z_s, errors)

def gen_five_param_subfin_avg(dataset_size, resolution=40):
    V = get_space(resolution)
    z_s = np.random.uniform(0.1, 1, (dataset_size, 5))
    phi = np.loadtxt('data/basis_five_param.txt',delimiter=",")
    phi = phi[:,0:10]
    solver = Fin(V)
    errors = np.zeros((dataset_size, 5))
    avgs = np.zeros((dataset_size, 5))
    avgs_r = np.zeros((dataset_size, 5))
    
    for i in range(dataset_size):
        w, y, A, B, C = solver.forward_five_param(z_s[i,:])
        avgs[i] = solver.qoi_operator(w)
        psi = np.dot(A, phi)
        A_r, B_r, C_r, x_r, y_r = solver.reduced_forward(A, B, C, psi, phi)
        avgs_r[i] = solver.reduced_qoi_operator(x_r)
        errors[i] = avgs[i] - avgs_r[i]

    return (z_s, errors)

def generate(dataset_size, resolution=40):
    '''
    Create a tensorflow dataset where the features are thermal conductivity parameters
    and the labels are the differences in the quantity of interest between the high 
    fidelity model and the reduced order model (this is the ROM error)

    Arguments: 
        dataset_size - number of feature-label pairs
        resolution   - finite element mesh resolution for the high fidelity model

    Returns:
        dataset      - Tensorflow dataset created from tensor slices
    '''

    V = get_space(resolution)
    dofs = len(V.dofmap().dofs())

    # TODO: Improve this by using mass matrix covariance. Bayesian prior may work well too
    z_s = np.random.uniform(0.1, 1, (dataset_size, dofs))
    phi = np.loadtxt('data/basis.txt',delimiter=",")
    solver = Fin(V)
    errors = np.zeros((dataset_size, 1))

    m = Function(V)
    for i in range(dataset_size):
        m.vector().set_local(z_s[i,:])
        w, y, A, B, C = solver.forward(m)
        psi = np.dot(A, phi)
        A_r, B_r, C_r, x_r, y_r = solver.reduced_forward(A, B, C, psi, phi)
        errors[i][0] = y - y_r 

    dataset = tf.data.Dataset.from_tensor_slices((z_s,errors))

    return dataset

def load_eval_dataset():
    '''
    Loads a validation dataset from disk
    '''
    try:
        z_s = np.loadtxt('data/z_s_eval.txt', delimiter=",")
        #  z_s = read_csv('data/z_s_train.txt', delimiter=",").values 
        errors = np.loadtxt('data/errors_eval.txt', delimiter=",", ndmin=2)
    except (FileNotFoundError, OSError) as err:
        print ("Error in loading saved training dataset. Run generate_and_save_dataset.")
        raise err

    return tf.data.Dataset.from_tensor_slices((z_s, errors))
    

def load_saved_dataset():
    '''
    Loads a training dataset from disk
    '''
    try:
        z_s = np.loadtxt('data/z_s_train.txt', delimiter=",")
        #  z_s = read_csv('data/z_s_train.txt', delimiter=",").values 
        errors = np.loadtxt('data/errors_train.txt', delimiter=",", ndmin=2)
    except (FileNotFoundError, OSError) as err:
        print ("Error in loading saved training dataset. Run generate_and_save_dataset.")
        raise err

    return tf.data.Dataset.from_tensor_slices((z_s, errors))

def generate_and_save_dataset(dataset_size, resolution=40):
    V = get_space(resolution)
    dofs = len(V.dofmap().dofs())
    z_s = np.random.uniform(0.1, 1, (dataset_size, dofs))
    phi = np.loadtxt('data/basis.txt',delimiter=",")
    solver = Fin(V)
    errors = np.zeros((dataset_size, 1))

    m = Function(V)
    for i in range(dataset_size):
        m.vector().set_local(z_s[i,:])
        w, y, A, B, C = solver.forward(m)
        psi = np.dot(A, phi)
        A_r, B_r, C_r, x_r, y_r = solver.reduced_forward(A, B, C, psi, phi)
        errors[i][0] = y - y_r 

    np.savetxt('data/z_s_train.txt', z_s, delimiter=",")
    np.savetxt('data/errors_train.txt', errors, delimiter=",")

def create_initializable_iterator(buffer_size, batch_size):
    z_s = np.loadtxt('data/z_s_train.txt', delimiter=",")
    #  z_s = read_csv('data/z_s_train.txt', delimiter=",").values
    errors = np.loadtxt('data/errors_train.txt', delimiter=",", ndmin=2)

    features_placeholder = tf.placeholder(z_s.dtype, z_s.shape)
    labels_placeholder = tf.placeholder(errors.dtype, errors.shape)

    dataset = tf.data.Dataset.from_tensor_slices((features_placeholder, labels_placeholder))

    iterator = dataset.shuffle(buffer_size).batch(batch_size).repeat().make_initializable_iterator()


class FinInput:
    '''
    A class to create a thermal fin instance with Tensorflow input functions
    '''
    def __init__(self, batch_size, resolution):
        self.resolution = resolution
        self.V = get_space(resolution)
        self.dofs = len(self.V.dofmap().dofs())
        self.phi = np.loadtxt('data/basis_five_param.txt',delimiter=",")
        self.batch_size = batch_size
        self.solver = Fin(self.V)

    def train_input_fn(self):
        params = np.random.uniform(0.1, 1, (self.batch_size, self.dofs))
        errors = np.zeros((self.batch_size, 1))

        for i in range(self.batch_size):
            m = Function(self.V)
            m.vector().set_local(params[i,:])
            w, y, A, B, C = self.solver.forward(m)
            psi = np.dot(A, self.phi)
            A_r, B_r, C_r, x_r, y_r = self.solver.reduced_forward(A, B, C, psi, self.phi)
            errors[i][0] = y - y_r 

        return ({'x':tf.convert_to_tensor(params)}, tf.convert_to_tensor(errors))

    def eval_input_fn(self):
        params = np.random.uniform(0.1, 1, (self.batch_size, self.dofs))
        errors = np.zeros((self.batch_size, 1))

        for i in range(self.batch_size):
            m = Function(self.V)
            m.vector().set_local(params[i,:])
            w, y, A, B, C = self.solver.forward(m)
            psi = np.dot(A, self.phi)
            A_r, B_r, C_r, x_r, y_r = self.solver.reduced_forward(A, B, C, psi, self.phi)
            errors[i][0] = y - y_r 

        return ({'x':tf.convert_to_tensor(params)}, tf.convert_to_tensor(errors))
