from django.conf import settings
import numpy as np
import simplejson as json
from twittersuck.spritzer.models import *
from csc.util.vector import pack64, unpack64
import sys
from stompy.simple import Client
import basic_stomp
import logging
import random

LOG_FILENAME = 'log/som.log'
#logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger('backend.som')

import numpy as np

import itertools
def cartesian(arrays, out=None):
    """
    Generate a cartesian product of input arrays.

    Parameters
    ----------
    arrays : list of array-like
        1-D arrays to form the cartesian product of.
    out : ndarray
        Array to place the cartesian product in.

    Returns
    -------
    out : ndarray
        2-D array of shape (M, len(arrays)) containing cartesian products
        formed of input arrays.

    Examples
    --------
    >>> cartesian(([1, 2, 3], [4, 5], [6, 7]))
    array([[1, 4, 6],
           [1, 4, 7],
           [1, 5, 6],
           [1, 5, 7],
           [2, 4, 6],
           [2, 4, 7],
           [2, 5, 6],
           [2, 5, 7],
           [3, 4, 6],
           [3, 4, 7],
           [3, 5, 6],
           [3, 5, 7]])

    """
    return np.asarray(list(itertools.product(*arrays)))

class SOMBuilder(object):
    def __init__(self, map_size=(100, 100), k=19, in_channel='/topic/SocNOC/twitter', out_channel='/topic/SocNOC/som'):
        host, port = settings.STOMP_HOSTS[0]
        self.stomp = Client(host, port)
        self.stompSender = basic_stomp.Connection(host_and_ports=settings.STOMP_HOSTS, user=settings.STOMP_USERNAME, passcode=settings.STOMP_PASSWORD)
        
        self.in_channel = in_channel
        self.out_channel = out_channel

        self.map_size = map_size
        self.k = k
        self.som_array = np.zeros(map_size+(k,))
        self.fill_array = np.zeros(map_size)
        self.size_array = np.zeros(map_size+(2,)) + 1
        self.text_array = []
        for x in xrange(map_size[0]):
            self.text_array.append([''] * map_size[1])
        
        self.sequence = []
        for x in xrange(map_size[0]):
            for y in xrange(map_size[0]):
                self.sequence.append((x, y))
        random.shuffle(self.sequence)
        self.seq_update = 0
        
        self.lookup = {}
        self.magnitudes = None

        self.initialize_som()


    def start(self):
        self.stomp.connect(username=settings.STOMP_USERNAME, password=settings.STOMP_PASSWORD)
        self.stomp.subscribe(destination=self.in_channel, ack='auto')
        self.stompSender.start()
        self.stompSender.connect()
        
        while True:
            msg = self.stomp.get()
            self.on_message(msg.body)
            
    def initialize_som(self):
        width, height = self.map_size
        self.som_array[:] = .1
        #for x in xrange(width):
        #    for y in xrange(height):
        #        self.som_array[x, y, 0] = 2.0*x / width - 1
        #        self.som_array[x, y, 1] = 2.0*y / height - 1
        #        self.som_array[x, y, 2] = 1

    def on_message(self, body):
        message = json.loads(body)
        if 'text' not in message:
            # metadata. skip it for now.
            return
        if message['text'].startswith('('):
            # skip features for now
            return
        self.magnitudes = unpack64(message['magnitudes'])[1:]
        self.handle_data(message)
        for concept in message['concepts']:
            vec = unpack64(message['concepts'][concept])[1:]
            product = vec * self.magnitudes
            self.handle_vector(product, concept)

    def handle_data(self, message):
        vec = unpack64(message['coordinates'])[1:]
        text = message['text']
        try:
            product = vec * self.magnitudes
        except ValueError:
            return
        self.handle_vector(product, text)

    def handle_vector(self, vec, text):
        # ... do SOM stuff
        if len(text) < 3:
            # too short, probably a stopword in some language
            return
        mag = np.sqrt(np.sum(vec * vec))
        vec = vec / np.linalg.norm(vec)
        if str(vec[0]).lower() == 'nan':
            log.warning("got zero vector for: %s" % text)
            log.warning("%s" % list(vec))
            return
        similarity = np.dot(self.som_array, vec)
        old_loc = self.lookup.get(text)
        if old_loc:
            oldx, oldy = old_loc
            if (oldx > 0 and oldx < self.map_size[0]-1 and
                oldy > 0 and oldy < self.map_size[1]-1):
                self.fill_array[oldx-1:oldx+1, oldy-1:oldy+1] = 0
        similarity *= (-self.fill_array + 2)
        best_loc = np.unravel_index(np.argmax(similarity), self.map_size)
        self.add_to_som(best_loc, vec, text, mag)

    def choose_size(self, text, mag):
        if text.startswith('@'):
            if len(text.split()) > 1:
                # it's a tweet. Make it small.
                return (2, 2)
            else:
                # it's a user... so we'll fit their user icon
                # in this box
                square = max(1, (np.log(mag)/np.log(10) + 9))
                return (square, square)
        elif text.find(' //') > -1:
            # it's a blog sentence. Make it small.
            return (2, 2)
        elif text.startswith('#'):
            # hashtag!
            size = max(1, (np.log(mag)/np.log(10) + 9))
            return (size*6, size)
        else:
            # it's a concept
            size = max(2, (np.log(mag)/np.log(10) + 8))
            return (size*4, size)
    
    def add_to_som(self, location, vec, text, mag):
        x, y = location
        old_vec = list(self.som_array[x, y, :])
        old_text = self.text_array[x][y]
        old_size = list(self.size_array[x, y, :])
        old_loc = self.lookup.get(text)
        
        width, height = self.choose_size(text, mag)
        radius = int(width)

        log.info(str((location, text, mag, radius)))
        
        xmin1 = max(0, x-radius)
        ymin1 = max(0, y-radius)
        xmax1 = min(self.map_size[0], x+radius+1)
        ymax1 = min(self.map_size[1], y+radius+1)
        while radius >= 1:
            xmin = max(0, x-radius)
            ymin = max(0, y-radius)
            xmax = min(self.map_size[0], x+radius+1)
            ymax = min(self.map_size[1], y+radius+1)
            
            slice = self.som_array[xmin:xmax, ymin:ymax]
            slice[:] = (slice*0.9 + vec*0.1)
            
            radius = radius * 3 / 4
        
        # now normalize all at once
        norms = np.sqrt(
          np.sum(self.som_array * self.som_array, axis=-1))
        self.som_array /= (norms[:,:,np.newaxis] + 0.001)
        
        # decay the fill array
        self.fill_array *= 0.998

        # update the center cell to refer exactly to this concept
        self.som_array[x, y, :] = vec
        self.size_array[x, y, :] = [width, height]
        self.text_array[x][y] = text
        self.fill_array[xmin1:xmax1,ymin1:ymax1] = 1
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

        #self.update_sequential()

    def update_sequential(self):
        x, y = self.sequence[self.seq_update]
        self.notify_listeners((x, y), self.som_array[x, y, :],
                              self.size_array[x, y, :], self.text_array[x][y])
        self.seq_update += 1
        if self.seq_update >= self.map_size[0] * self.map_size[1]:
            random.shuffle(self.sequence)
            self.seq_update = 0
    
    def notify_listeners(self, location, vec, size, text):
        img = ''
        if text.startswith('@') and len(text.split()) == 1:
            try:
                user = User.objects.get(username=text[1:])
                img = user.profile_image_url
                assert size[0] == size[1]
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                return
        message = {
            'text': text,
            'x': int(location[0]),
            'y': int(location[1]),
            'coordinates': pack64(vec),
            'width': int(size[0]),
            'height': int(size[1]),
            'img': img
        }
        self.send(message)
    
    def send(self,data):    
        msg = json.dumps(data)
        self.stompSender.send(msg, destination=self.out_channel)

def main():
    som = SOMBuilder()
    som.start()

if __name__ == '__main__': main()
