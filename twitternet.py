import logging, logging.handlers
import socket
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'vectornet'))
import utils

from twisted.python import log
rootLogger = logging.getLogger('')
rootLogger.setLevel(logging.INFO)
logger = logging.getLogger(socket.gethostname())
logger.addHandler(logging.FileHandler('log'))
log.startLogging(sys.stdout)

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
        logger.info('TwitterStream: %s with frame %d' % (data, self.frame_number))
        if 'delete' in data:
            return
        self.sendMessage({ 'vector' : data, 'frame_number' : self.frame_number })
        self.frame_number += 1

class TwitterProcess(utils.BasicNode):
    def __init__(self, router, nodeDict):
        utils.BasicNode.__init__(self, router, nodeDict)
        self.frame_number = 1
        
        from backend.snoc_backend import SocNOC
        self.snoc = SocNOC('/dummy')
        def send(data):
            logger.info('TwitterProcess: %s with frame %d' % (data, self.frame_number))
            self.sendMessage({ 'vector' : data, 'frame_number' : self.frame_number })
            self.frame_number += 1
        self.snoc.send = send

    def calculatePriority(self, received_frame, current_frame):
        return received_frame

    def compute(self, data):
        for tweet in data.values():
            self.snoc.receiveTweet(tweet)

### TODO Try one with SOM? TODO
