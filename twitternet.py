import logging, socket, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'vectornet'))
import utils

rootLogger = logging.getLogger('')
rootLogger.setLevel(logging.INFO)
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
    logger.info('\033[1;31m%s\033[0m: %s' % (obj.__class__.__name__, msg))

class TwitterStream(utils.ProducingNode):
    def __init__(self, router, nodeDict):
        utils.ProducingNode.__init__(self, router, nodeDict)
        self.frame_number = 1
        
        import tweetstream
        from twittersuck.db_password import TWITTER_USER, TWITTER_PASSWORD
        from twittersuck.settings import TWITTER_FEED
        self.stream = tweetstream.ReconnectingTweetStream(TWITTER_USER, TWITTER_PASSWORD, url=TWITTER_FEED)
        
    def compute(self):
        data = self.stream.next()
        log(self, '%s with frame %d' % (data.keys(), self.frame_number))
        if 'delete' in data:
            return
        self.sendMessage({ 'vector' : data, 'frame_number' : self.frame_number })
        self.frame_number += 1 # this might desync with TwitterProcess

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
        self.som = SOMBuilder()
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
