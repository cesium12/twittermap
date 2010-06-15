import numpy as np
from backend.som import SOMBuilder, log

class RedFishBlueFishSOM(SOMBuilder):
    def handle_vector(self, vec, text):
        if text == u'#democrat' or text.endswith(u'-#republican'):
            self.handle_fixed_vector(vec, text, -1, -1)
        elif text == u'#republican' or text.endswith(u'-#democrat'):
            self.handle_fixed_vector(vec, text, 1, 1)
        SOMBuilder.handle_vector(self, vec, text)
    
    def handle_fixed_vector(self, vec, text, xfactor, yfactor):
        width, height = self.map_size
        gradient=(np.linspace(0, .1, width)[::xfactor, np.newaxis]+
                  np.linspace(0, .1, height)[np.newaxis, ::yfactor])
        delta = gradient[:,:,np.newaxis] * vec
        self.som_array += delta
        
    def add_to_som(self, location, vec, text, mag):
        x, y = location
        old_vec = list(self.som_array[x, y, :])
        old_text = self.text_array[x][y]
        old_size = list(self.size_array[x, y, :])
        old_loc = self.lookup.get(text)
        
        width, height = self.choose_size(text, mag)
        radius = int(width)

        log.info(str((location, text, mag, radius)))
        
        # normalize everything
        norms = np.sqrt(
          np.sum(self.som_array * self.som_array, axis=-1))
        self.som_array /= (norms[:,:,np.newaxis] + 0.001)

        while radius >= 1:
            xmin = max(0, x-radius)
            ymin = max(0, y-radius*2)
            xmax = min(self.map_size[0], x+radius+1)
            ymax = min(self.map_size[1], y+radius*2+1)
            
            slice = self.som_array[xmin:xmax, ymin:ymax]
            slice[:] = (slice + vec) / 2
            radius /= 2
            
        # normalize everything again
        norms = np.sqrt(
          np.sum(self.som_array * self.som_array, axis=-1))
        self.som_array /= (norms[:,:,np.newaxis] + 0.001)
        
        # decay the fill array
        self.fill_array *= 0.998

        # update the center cell to refer exactly to this concept
        self.som_array[x, y, :] = vec
        self.size_array[x, y, :] = [width, height]
        self.text_array[x][y] = text
        self.fill_array[x,y] = 1
        self.notify_listeners(location, vec, [width, height], text)
        self.lookup[text] = location
        
        # if the concept is moving, do a swap
        if old_loc:
            self.som_array[old_loc[0], old_loc[1], :] = old_vec
            self.size_array[old_loc[0], old_loc[1], :] = [1, 1]
            self.notify_listeners(old_loc, old_vec, [1, 1], '')
            self.fill_array[old_loc[0]][old_loc[1]] = 0
            self.text_array[old_loc[0]][old_loc[1]] = ''
            if old_text:
                self.text_array[old_loc[0]][old_loc[1]] = old_text
                self.size_array[old_loc[0]][old_loc[1]] = old_size
                self.fill_array[old_loc[0]][old_loc[1]] = 1
                self.lookup[old_text] = old_loc
                self.notify_listeners(old_loc, old_vec, old_size, old_text)

def main():
    som = RedFishBlueFishSOM(k=9, map_size=(80, 60), in_channel='/topic/SocNOC/redfishbluefish', out_channel='/topic/SocNOC/somfish')
    som.start()

if __name__ == '__main__': main()
