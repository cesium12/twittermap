import logging, socket, os, sys, re, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'vectornet'))
import utils

rootLogger = logging.getLogger('')
rootLogger.setLevel(25)
logger = logging.getLogger(socket.gethostname())
#logger.addHandler(logging.FileHandler('log'))
#from twisted.python import log
#log.startLogging(sys.stdout)

handler = None
def log(obj, msg): # XXX change to network logging?
    global handler
    if handler is None:
        handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(handler)
    logger.log(25, '\033[1;31m%s\033[0m: %s' % (obj.node['name'], msg))

class TwitterStream(utils.ProducingNode):
    'Reads from the Twitter "sample" stream, producing an arbitrary selection of tweets.'
    
    def __init__(self, router, nodeDict):
        utils.ProducingNode.__init__(self, router, nodeDict)
        self.frame_number = 1
    
    def startProducing(self):
        from twittersuck.db_password import TWITTER_USER, TWITTER_PASSWORD
        import TwistedTwitterStream
        
        class Consumer(TwistedTwitterStream.TweetReceiver):
            def connectionFailed(this, why):
                log(self, 'connection failed (%s)' % why)
            def tweetReceived(this, data):
                if 'delete' not in data:
                    log(self, '%s with frame %d' % (data.keys(), self.frame_number))
                    self.sendMessage({ 'vector' : data, 'frame_number' : self.frame_number })
                    self.frame_number += 1 # XXX might desync with TwitterProcess
        
        TwistedTwitterStream.sample(TWITTER_USER, TWITTER_PASSWORD, Consumer())

class TwitterProcess(utils.BasicNode):
    'Uses SocNOC to apply common-sense data to tweets.'
    
    def __init__(self, router, nodeDict):
        utils.BasicNode.__init__(self, router, nodeDict)
        self.frame_number = 1
        
        from backend.snoc_backend import SocNOC
        self.snoc = SocNOC('/dummy')
        def send(data):
            log(self, '%s with frame %d' % (data.keys(), self.frame_number))
            self.sendMessage({ 'vector' : data, 'frame_number' : self.frame_number })
            self.frame_number += 1
        self.snoc.send = send
    
    def calculatePriority(self, received_frame, current_frame):
        return received_frame
    
    def compute(self, data):
        for tweet in data.values():
            self.snoc.receiveTweet(tweet)

class TwitterSom(utils.BasicNode):
    'Uses SOMBuilder to construct SOMs out of processed tweets.'
    
    def __init__(self, router, nodeDict):
        utils.BasicNode.__init__(self, router, nodeDict)
        self.frame_number = 1
        
        from backend.som import SOMBuilder
        self.som = SOMBuilder(k=19, map_size=(100, 80))
        def send(data):
            log(self, '%s with frame %d' % (data.keys(), self.frame_number))
            self.sendMessage({ 'vector' : data, 'frame_number' : self.frame_number })
        self.som.send = send
    
    def calculatePriority(self, received_frame, current_frame):
        return received_frame
    
    def compute(self, data):
        for tweet in data.values():
            self.som.on_message(tweet)
        self.frame_number += 1

class TwitterSpecificStream(utils.ProducingNode):
    'Reads from the Twitter "filter" stream, producing tweets that match given keywords.'
    
    def __init__(self, router, nodeDict):
        utils.ProducingNode.__init__(self, router, nodeDict)
        self.frame_number = 1
        self.regex = re.compile('|'.join([x.lower() for x in self.node['wl']]), re.I)
    
    def startProducing(self):
        from twittersuck.db_password import TWITTER_USER, TWITTER_PASSWORD
        import TwistedTwitterStream
        
        class Consumer(TwistedTwitterStream.TweetReceiver):
            def connectionFailed(this, why):
                log(self, 'connection failed (%s)' % why)
            def tweetReceived(this, data):
                if 'delete' not in data and data['user'] and self.regex.search(data['text']):
                    log(self, '%s with frame %d' % (data.keys(), self.frame_number))
                    self.sendMessage({ 'vector' : data, 'frame_number' : self.frame_number })
                    self.frame_number += 1
        
        TwistedTwitterStream.filter(TWITTER_USER, TWITTER_PASSWORD, Consumer(), track=[x.split(None, 1)[0] for x in self.node['wl']])

class RfbfStream(utils.ProducingNode):
    'Reads and processes entries from political feeds.'
    
    def __init__(self, router, nodeDict):
        utils.ProducingNode.__init__(self, router, nodeDict)
        self.frame_number = 1
        
        from backend.snoc_backend import SocNOC, weave_streams
        self.snoc = SocNOC('/dummy', k=10, spicefreq=0, cnetfreq=0)
        from backend.affect_values import affect
        self.snoc.categories = {
            'affect' : affect,
            'politics' : { '#republican' : 1, '#democrat' : -1 },
            'person' : { 'person' : 1 }
        }
        def send(data):
            log(self, '%s with frame %d' % (data, self.frame_number))
            self.sendMessage({ 'vector' : data, 'frame_number' : self.frame_number })
            self.frame_number += 1
        self.snoc.send = send
        
        with open(self.node['rfile']) as rfile:
            rep = [(line.strip(), ' #republican -#democrat') for line in rfile]
        with open(self.node['dfile']) as dfile:
            dem = [(line.strip(), ' #democrat -#republican') for line in dfile]
        def stream():
            while True:
                for s in self.snoc._process_feed_list(weave_streams([rep, dem])):
                    yield s
        self.stream = stream()
    
    def compute(self): # XXX not Twisted... maybe should be?
        self.snoc._process_feed_item(*next(self.stream))

class RfbfSom(utils.BasicNode):
    'Constructs SOMs out of RFBF items.'
    
    def __init__(self, router, nodeDict):
        utils.BasicNode.__init__(self, router, nodeDict)
        self.frame_number = 1
        
        from backend.somfish import RedFishBlueFishSOM
        self.som = RedFishBlueFishSOM(k=9, map_size=(80, 60))
        def send(data):
            log(self, '%s with frame %d' % (data.keys(), self.frame_number))
            self.sendMessage({ 'vector' : data, 'frame_number' : self.frame_number })
        self.som.send = send
    
    def calculatePriority(self, received_frame, current_frame):
        return received_frame
    
    def compute(self, data):
        for datum in data.values():
            self.som.on_message(datum)
        self.frame_number += 1

class RfbfVec(utils.BasicNode):
    'Does math to position concepts on a plane.'
    
    def __init__(self, router, nodeDict):
        utils.BasicNode.__init__(self, router, nodeDict)
        self.frame_number = 1
        
        from csc.util.vector import unpack64
        import numpy
        def unpack(dct):
            ret = {}
            for k, v in dct.items():
                ret[k] = unpack64(v)[1:]
            return ret
        def orthogonalize(vec1, vec2):
            return vec2 - vec1 * numpy.vdot(vec1, vec2) / numpy.vdot(vec1, vec1)
        
        self.unpack = unpack
        self.norm = numpy.linalg.norm
        self.vdot = numpy.vdot
        self.orthogonalize = orthogonalize
    
    def calculatePriority(self, received_frame, current_frame):
        return received_frame
    
    def compute(self, data):
        for datum in data.values():
            if datum.get('text', None) and datum['text'][0] != '(':
                categories, concepts = self.unpack(datum['categories']), self.unpack(datum['concepts'])
                if not all([ vec.any() for vec in categories.values() ]):
                    continue # ignore if any zero vectors
                politics = self.orthogonalize(categories['person'], categories['politics'])
                affect = self.orthogonalize(politics, categories['affect'])
                pnorm, anorm = self.norm(politics), self.norm(affect)
                concepts.pop('empty', None) # ignore 'empty' concept if it exists
                for con, vec in concepts.items():
                    vnorm = self.norm(vec)
                    self.output(concept=con, text=datum['text'],
                                size=float(math.sqrt(math.sqrt(vnorm))),
                                x=float(self.vdot(politics, vec) / pnorm / vnorm),
                                y=float(self.vdot(affect, vec) / anorm / vnorm))
        self.frame_number += 1
    
    def output(self, **data):
        log(self, '%s with frame %d' % (data, self.frame_number))
        self.sendMessage({ 'vector' : data, 'frame_number' : self.frame_number })
