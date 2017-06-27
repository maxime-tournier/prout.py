from __future__ import print_function
import numpy as np

from numpy.polynomial.polynomial import Polynomial

from snap.math import *
from snap.gl import *

from snap import viewer, tool, spline




    

n = 10

nodes = np.linspace(-100, 100, n)

m = 2000       
sampled_nodes = np.linspace(nodes[0], nodes[-1], m)


rigids = 10 * (np.random.rand(n, 7) - 0.5)

for i in range(n):
    rigids[i].view(Rigid3).orient.normalize()
    
frame = 0

rigid_spline = spline.Spline(nodes, rigids, spline.TranslationRotationGroup())

sampled_rigids = [rigid_spline(x)[0] for x in sampled_nodes]
sampled_drigids = [rigid_spline(x)[1] for x in sampled_nodes]


class State(object): pass
state = State()

state.g = sampled_rigids[0]
state.dg = sampled_drigids[0]

state.frame = 0


def animate():

    state.frame = (state.frame + 1) % m

    state.g[:] = sampled_rigids[state.frame]
    state.dg[:] = sampled_drigids[state.frame]
    
    
def draw():
    m = 100

    glDisable(GL_LIGHTING)
    glPointSize(5)

    # curve + control points
    glColor(1, 0, 0)
            
    glBegin(GL_LINE_STRIP)    
    glColor(1, 1, 1)
    
    for g in sampled_rigids:
        glVertex(g.view(Rigid3).center)
    glEnd()

    
    
    glEnable(GL_LIGHTING)

    for g in rigids:
        g = g.view(Rigid3)
        with push_matrix():
            glTranslate(*g.center)
            
            rotate(g.orient)
            glScale(0.6, 0.6, 0.6)
            viewer.draw_axis()
            

    
    # interpolated frame
    with push_matrix():
        glTranslate(*state.g.center)

        with push_matrix():
            rotate(state.g.orient)
            viewer.draw_axis()

        # angular velocity
        with lookat(state.dg.angular):
            glColor(1, 0, 1)
            arrow(height = norm(state.dg.angular))        

        with lookat(state.dg.linear):
            glColor(1, 1, 0)
            arrow(height = norm(state.dg.linear))        
        

        
if __name__ == '__main__':
    viewer.run()




