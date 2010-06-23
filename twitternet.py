import logging, socket, os, sys, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'vectornet'))
import utils

rootLogger = logging.getLogger('')
rootLogger.setLevel(25)
logger = logging.getLogger(socket.gethostname())
#logger.addHandler(logging.FileHandler('log'))
#from twisted.python import log
#log.startLogging(sys.stdout)

handler = None
def log(obj, msg): # change to network logging?
    global handler
    if handler is None:
        handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(handler)
    logger.log(25, '\033[1;31m%s\033[0m: %s' % (obj.node['name'], msg))

class TwitterBlockingStream(utils.ProducingNode):
    def __init__(self, router, nodeDict):
        utils.ProducingNode.__init__(self, router, nodeDict)
        self.frame_number = 1
        
        import tweetstream
        from twittersuck.db_password import TWITTER_USER, TWITTER_PASSWORD
        from twittersuck.settings import TWITTER_FEED
        self.stream = tweetstream.ReconnectingTweetStream(TWITTER_USER, TWITTER_PASSWORD, url=TWITTER_FEED)
    
    def compute(self):
        data = self.stream.next()
        if 'delete' not in data:
            log(self, '%s with frame %d' % (data.keys(), self.frame_number))
            self.sendMessage({ 'vector' : data, 'frame_number' : self.frame_number })
            self.frame_number += 1

class TwitterTwittyStream(utils.ProducingNode):
    def __init__(self, router, nodeDict):
        utils.ProducingNode.__init__(self, router, nodeDict)
        self.frame_number = 1
    
    def startProducing(self):
        from twittersuck.db_password import TWITTER_USER, TWITTER_PASSWORD
        from twittytwister import twitter
        from twittytwister.txml import BaseXMLHandler
        
        def handlerToDict(h):
            if isinstance(h, BaseXMLHandler):
                return handlerToDict(h.__dict__)
            elif isinstance(h, dict):
                ret = {}
                for k, v in h.items():
                    ret[k] = handlerToDict(v)
                return ret
            elif isinstance(h, (list, tuple)):
                return [ handlerToDict(x) for x in h ]
            elif isinstance(h, type):
                return None
            else:
                return h
        
        def delegate(data):
            data = handlerToDict(data)
            if 'delete' not in data and data['user']:
                log(self, '%s with frame %d' % (data.keys(), self.frame_number))
                self.sendMessage({ 'vector' : data, 'frame_number' : self.frame_number })
                self.frame_number += 1
        
        twitter.TwitterFeed(TWITTER_USER, TWITTER_PASSWORD).sample(delegate).addErrback(logger.error)

class TwitterStream(utils.ProducingNode):
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
                    self.frame_number += 1 # this might desync with TwitterProcess
        
        TwistedTwitterStream.sample(TWITTER_USER, TWITTER_PASSWORD, Consumer())

class TwitterProcess(utils.BasicNode):
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
