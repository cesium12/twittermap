import simplejson as json
import numpy as np

class SOMBuilder(object):
    def __init__(self, map_size=(100, 100), k=20):
        self.map_width, self.map_height = map_size
        self.som_array = np.zeros(map_size + (k-1,)) + 0.1
        self.fill_array = np.zeros(map_size)
        self.size_array = np.zeros(map_size + (2,)) + 1
        self.text_array = np.zeros(map_size, str).astype(object)
        self.lookup = {}
    
    def on_message(self, message):
        text = message.get('text', None)
        if text and text[0] != '(':
            magnitudes = np.array(message['magnitudes'])[1:]
            coordinates = np.array(message['coordinates'])[1:]
            try:
                self.handle_vector(coordinates * magnitudes, text)
            except ValueError:
                pass
            for concept, pos in message['concepts'].items():
                self.handle_vector(np.array(pos)[1:] * magnitudes, concept)
    
    def normalize(self, eps=0.001):
        norms = np.sqrt((self.som_array * self.som_array).sum(axis=-1))[:,:,np.newaxis]
        self.som_array /= (norms + eps)
    
    def region(self, location, radius, rratio):
        x, y = location
        return ( slice(max(0, x - radius),
                       min(self.map_width, x + radius + 1)),
                 slice(max(0, y - radius * rratio),
                       min(self.map_height, y + radius * rratio + 1)) )
    
    def handle_vector(self, vec, text, rratio=1, rstep=0.75, sratio = 0.9, fdecay=0.998, nbefore=False):
        mag = np.linalg.norm(vec)
        vec /= mag
        if np.isnan(vec).any() or len(text) < 3:
            return
        if text.startswith('@'):
            if len(text.split()) > 1: # tweet
                width = height = 2
            else: # user
                width = height = max(1, np.log10(mag) + 9)
        elif text.find(' //') > -1: # blog
            width = height = 2
        elif text.startswith('#'): # hash
            size = max(1, np.log10(mag) + 9)
            width, height = size * 6, size
        else: # concept
            size = max(2, np.log10(mag) + 8)
            width, height = size * 4, size
        
        similarity = np.dot(self.som_array, vec) * (2 - self.fill_array)
        loc = np.unravel_index(np.argmax(similarity), (self.map_width, self.map_height))
        
        old_loc = self.lookup.get(text)
        old_vec = list(self.som_array[loc])
        old_size = list(self.size_array[loc])
        old_text = self.text_array[loc]
        
        if nbefore:
            self.normalize()
        self.fill_array *= fdecay
        radius = int(width)
        region = self.region(loc, radius, rratio)
        self.fill_array[region] = 1
        while radius >= 1:
            self.som_array[region] *= sratio
            self.som_array[region] += vec * (1 - sratio)
            radius = int(radius * rstep)
            region = self.region(loc, radius, rratio)
        self.normalize()
        
        self.lookup[text] = loc
        self.notify_listeners(loc, vec, text, [width, height])
        if old_loc:
            if old_text:
                self.lookup[old_text] = old_loc
            else:
                old_size = [1, 1]
            self.notify_listeners(old_loc, old_vec, old_text, old_size)
    
    def notify_listeners(self, loc, vec, text, size):
        self.som_array[loc] = vec
        self.text_array[loc] = text
        self.fill_array[loc] = bool(text)
        self.size_array[loc] = (width, height) = size
        self.send({ 'text'  : text,        'img'    : '',
                    'x'     : int(loc[0]), 'y'      : int(loc[1]),
                    'width' : int(width),  'height' : int(height),
                    'coordinates' : list(vec) })
    
    def send(self, data): # override this method
        print json.dumps(data)
