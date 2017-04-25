# MIT license
# tournier.maxime@gmail.com
'''rigid-body kinematics'''

from __future__ import print_function, absolute_import

import numpy as np

import math
import sys


from numpy.linalg import norm

def vec(*coords):
    return np.array(coords, dtype = float)


deg = 180.0 / math.pi

ex = vec(1, 0, 0)
ey = vec(0, 1, 0)
ez = vec(0, 0, 1)

# slices for quaternion/rigid/deriv
imag_slice = slice(None, 3)
real_index = -1

angular_slice = slice(3, None)
linear_slice = slice(None, 3)

orient_slice = slice(3, None)
center_slice = slice(None, 3)



class Rigid3(np.ndarray):
    dim = 6

    __slots__ = ()
    
    class Deriv(np.ndarray):
        '''lie algebra element as (translation, rotation)'''
        __slots__ = ()

        def __new__(cls, *args, **kwargs):
            return np.ndarray.__new__(cls, 6)

        def __init__(self):
            self[:] = 0

        @property
        def linear(self):
            return self[ linear_slice ].view( np.ndarray )

        @linear.setter
        def linear(self, value):
            self[ linear_slice ] = value

        
        @property
        def angular(self):
            return self[ angular_slice ].view( np.ndarray )

        @angular.setter
        def angular(self, value):
            self[ angular_slice ] = value


    @property
    def center(self):
        '''translation'''
        return self[:3].view( np.ndarray )

    @center.setter
    def center(self, value):
        self[:3] = value

    @property
    def orient(self):
        '''rotation quaternion'''
        return self[3:].view(Quaternion)

    @orient.setter
    def orient(self, value):
        self[3:] = value

    def __new__(cls, *args, **kwargs):
        return np.ndarray.__new__(cls, 7)
        
    def __init__(self, **kwargs):
        # TODO w should go first
        self[-1] = 1
        self[:6] = 0

        for k, v in kwargs.items(): setattr(self, k, v)
        
    def inv(self):
        '''invert rigid transformations'''
        res = Rigid3()
        res.orient = self.orient.inv()
        res.center = -res.orient(self.center)
        return res

    def __mul__(self, other):
        '''compose rigid transformations'''
        res = Rigid3()

        res.orient = self.orient * other.orient
        res.center = self.center + self.orient(other.center)
        
        return res

    def __call__(self, x):
        '''applies rigid transform to vector x'''
        return self.center + self.orient(x)


    def Ad(self):
        '''SE(3) group adjoint matrix'''
        
        res = np.zeros((6, 6))

        R = self.orient.matrix()
        t = Quaternion.hat(self.center)

        ang = angular_slice
        lin = linear_slice
        
        res[ang, ang] = R
        res[lin, lin] = R
        
        res[lin, ang] = t.dot(R)

        return res


    def matrix(self):
        '''homogeneous matrix for rigid transformation'''

        res = np.zeros( (4, 4) )
        res[:3, :3] = self.orient.matrix()
        res[:3, 3] = self.center

        res[3, 3] = 1

        return res


    @staticmethod
    def exp(x):
        '''SE(3) exponential'''
        
        res = Rigid3()

        res.orient = Quaternion.exp( x.angular )
        res.center = res.orient( Quaternion.dexp( x.angular ).dot( x.linear ) )

        return res

    
    def log(self):
        '''SE(3) logarithm'''
        res = Rigid3.Deriv()

        res.angular = self.orient.log()
        res.linear = self.orient.dlog().dot( self.orient.conj()( self.center ) )

        return res



    
    
class Quaternion(np.ndarray):
    __slots__ = ()
    
    dim = 3
    epsilon = sys.float_info.epsilon
    
    def __new__(cls, *args):
        return np.ndarray.__new__(cls, 4)
        
    def __init__(self):
        '''identity quaternion'''
        self.real = 1
        self.imag = 0
        
    def inv(self):
        '''inverse'''
        return self.conj() / self.dot(self)
    
    def conj(self):
        '''conjugate'''
        res = Quaternion()
        res.real = self.real
        res.imag = -self.imag

        return res

    @property
    def real(self):
        '''real part'''
        return self[real_index]

    @real.setter
    def real(self, value):
        self[real_index] = value

    @property
    def imag(self):
        '''imaginary part'''
        return self[imag_slice].view( np.ndarray )

    @imag.setter
    def imag(self, value): self[imag_slice] = value

    def normalize(self):
        '''normalize quaternion'''
        self /= norm(self)

    def flip(self):
        '''flip quaternion in the real positive halfplane, if needed'''
        if self.real < 0: self = -self

    def __mul__(self, other):
        '''quaternion product'''
        res = Quaternion()
        
        res.real = self.real * other.real - self.imag.dot(other.imag)
        res.imag = self.real * other.imag + other.real * self.imag + np.cross(self.imag, other.imag)
        
        return res
         

    def __call__(self, x):
        '''rotate a vector. self should be normalized'''

        cross = np.cross(self.imag, x)
        return x + (2 * self.real) * cross + np.cross(self.imag, cross)
    
    # TODO optimize ?
    def matrix(self):
        '''rotation matrix'''

        K = Quaternion.hat(self.imag)
        return np.identity(3) + (2*self.real) * K + K.dot(K)
        
    
    @staticmethod
    def exp(x):
        '''quaternion exponential (halved)'''

        x = np.array( x )
        theta = norm(x)

        res = Quaternion()
        
        if math.fabs(theta) < Quaternion.epsilon:
            res.imag = x / 2.0
            res.normalize()
            return res

        half_theta = theta / 2.0
        
        s = math.sin(half_theta)
        c = math.cos(half_theta)

        res.real = c
        res.imag = x * (s / theta)

        return res

    
    @staticmethod
    def dexp(x):
        '''exponential derivative (SO(3)) in body-fixed coordinates'''

        theta = norm(x)

        if theta < Quaternion.epsilon:
            return np.identity(3)
        
        n = x / theta
        
        P = np.outer(n, n)
        H = Quaternion.hat(n)

        # we want SO(3) exponential
        theta = theta / 2.0
        
        s = math.sin(theta)
        c = math.cos(theta)

        I = np.identity(3)

        return P + (s / theta) * (c * I - s * H).dot(I - P)


    def dlog(self):
        '''logarithm derivative (SO(3)) in body-fixed coordinates'''
        
        n, theta = self.axis_angle()
        
        if n is None: return np.identity(3)

        theta /= 2
        res = np.zeros( (3, 3) )

        P = np.outer(n, n)

        log = n * theta
        
        return (P + (theta / math.tan(theta)) * ( np.identity(3) - P ) + Quaternion.hat(log) )

    
    def log(self):
        '''quaternion logarithm (doubled)'''

        axis, angle = self.axis_angle()

        if axis is None: return np.zeros(3)
        return angle * axis
    

    def axis_angle(self):
        '''rotation axis/angle'''

        q = self if self.real >= 0 else -self
        
        half_angle = math.acos( min(q.real, 1.0) )

        if half_angle > Quaternion.epsilon:
            return q.imag / math.sin(half_angle), 2 * half_angle

        n = norm(q.imag)
        if n > Quaternion.epsilon:
            sign = 1.0 if half_angle > 0 else -1.0
            return q.imag * (sign / n), 2 * half_angle
        
        return None, 2 * half_angle

    
    @staticmethod
    def from_vectors(x, y):
        '''rotation sending x to y'''
        
        res = Quaternion()

        dot = x.dot(y)
        res.real = dot
        res.imag = np.cross(x, y)

        theta = norm(res)
        res.real += theta

        theta = norm(res)
        if theta < Quaternion.epsilon:

            # x == y
            if dot >= 0: return Quaternion()
            
            # x == -y
            # TODO make up vector configurable
            return Quaternion.exp( math.pi * ey )
            
        res /= theta
        return res


    def Ad(self):
        return self.matrix()
    
    @staticmethod
    def hat(v):
        '''cross-product matrix'''
        
        res = np.zeros( (3, 3) )

        res[:] = [[    0, -v[2],  v[1]],
                  [ v[2],     0, -v[0]],
                  [-v[1],  v[0],     0]]

        return res


    def slerp(self, q2, t):
        '''spherical linear interpolation between q1 and q2'''
        # TODO optimize
        return self * Quaternion.exp( t * (self.conj() * q2).log() )
