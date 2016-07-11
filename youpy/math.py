# MIT license
# tournier.maxime@gmail.com

'''rigid-body kinematics'''

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

class Rigid3(np.ndarray):

    # note: lie algebra coordinates are (rotation, translation)

    # TODO: make a twist class ?
    
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

    def __new__(cls, *args):
        return np.ndarray.__new__(cls, 7)
        
    def __init__(self):
        # TODO w should go first
        self[-1] = 1
        self[:6] = 0
        
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

        
        res[:3, :3] = R
        res[3:, 3:] = R

        res[3:, :3] = t.dot(R)

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

        res.orient = Quaternion.exp( x[:3] )
        res.center = res.orient( Quaternion.dexp( x[:3] ).dot( x[3:] ) )

        return res

    
    def log(self):

        res = np.zeros(6)

        res[:3] = self.orient.log()
        res[3:] = self.orient.dlog().dot( self.orient.conj()( self.center ) )

        return res
    
    
class Quaternion(np.ndarray):

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
        return self[-1]

    @real.setter
    def real(self, value):
        self[-1] = value

    @property
    def imag(self):
        '''imaginary part'''
        return self[:3].view( np.ndarray )

    @imag.setter
    def imag(self, value): self[:3] = value

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
        
        tmp = Quaternion()
        tmp.real = 0
        tmp.imag = x

        return (self * tmp * self.conj()).imag


    # TODO this is horribly inefficient, optimize
    def matrix(self):
        '''rotation matrix'''

        R = np.identity(3)

        for i in range(3):
            R[:, i] = self( np.eye(1, 3, i) )

        return R
        
    
    @staticmethod
    def exp(x):
        '''quaternion exponential (halved)'''

        x = np.array( x )
        theta = norm(x)

        res = Quaternion()
        
        if math.fabs(theta) < Quaternion.epsilon:
            res.imag = x / 2.0
            # res.normalize()
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
    

    def angle(self):
        '''rotation angle'''
        return 2 * math.acos(self.real)

    def axis(self):
        '''rotation axis'''
        return self.imag / math.sin(  math.acos(self.real) )


    def axis_angle(self):
        '''rotation axis/angle'''

        q = self if self.real >= 0 else -self
        
        half_angle = math.acos( min(q.real, 1.0) )
        axis = q.imag / math.sin( half_angle ) if half_angle > Quaternion.epsilon else None

        return axis, 2 * half_angle

    
    @staticmethod
    def from_vectors(x, y):
        '''rotation sending x to y'''
        
        res = Quaternion()

        res.real = x.dot(y)
        res.imag = np.cross(x, y)

        theta = norm(res)
        res.real += theta

        theta = norm(res)
        if theta < Quaternion.epsilon:
            # pi rotation, axis is arbitrary (pick ey)
            # TODO make up vector configurable
            return Quaternion.exp( math.pi * ey )
            
        res /= theta
        return res
    
    
    @staticmethod
    def hat(v):
        '''cross-product matrix'''
        
        res = np.zeros( (3, 3) )

        res[0, 1] = -v[2]
        res[0, 2] = v[1]
        res[1, 2] = -v[0]

        res -= res.T

        return res


    
