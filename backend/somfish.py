import numpy as np
from backend.som import SOMBuilder

class SOMFish(SOMBuilder):
    def handle_vector(self, vec, text):
        if text == u'#democrat' or text.endswith(u'-#republican'):
            self.handle_fixed_vector(vec, text, -1, -1)
        elif text == u'#republican' or text.endswith(u'-#democrat'):
            self.handle_fixed_vector(vec, text, 1, 1)
        SOMBuilder.handle_vector(self, vec, text, rratio=2, rstep=0.5, sratio=0.5, nbefore=True)
    
    def handle_fixed_vector(self, vec, text, xfactor, yfactor):
        gradient = ( np.linspace(0, .1, self.map_width)[::xfactor,np.newaxis] +
                     np.linspace(0, .1, self.map_height)[np.newaxis,::yfactor] )
        self.som_array += gradient[:,:,np.newaxis] * vec
