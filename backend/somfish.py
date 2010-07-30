import numpy as np
from backend.som import SOMBuilder

class SOMFish(SOMBuilder):
    def __init__(self, fixed, *args, **kwargs):
        SOMBuilder.__init__(self, *args, **kwargs)
        self.fixed = fixed
    
    def handle_vector(self, vec, text):
        for eq, end, x, y in self.fixed:
            if text == eq or text.endswith(end):
                self.handle_fixed_vector(vec, text, x, y)
        SOMBuilder.handle_vector(self, vec, text, rratio=2, rstep=0.5, sratio=0.5, nbefore=True)
    
    def handle_fixed_vector(self, vec, text, xfactor, yfactor):
        gradient = ( np.linspace(0, .1, self.map_width)[::xfactor,np.newaxis] +
                     np.linspace(0, .1, self.map_height)[np.newaxis,::yfactor] )
        self.som_array += gradient[:,:,np.newaxis] * vec
