import logging, socket, sys, re, numpy, pickle
import TwistedTwitterStream
from backend.snoc import SocNOC
from vectornet.utils import ProducingNode, BasicNode, ACCEPTED
from secrets import TWITTER_USER, TWITTER_PASSWORD

rootLogger = logging.getLogger('')
rootLogger.setLevel(25)
logger = logging.getLogger(socket.gethostname())
#logger.addHandler(logging.FileHandler('log'))

handler = None
def log(obj, msg):
    global handler
    if handler is None:
        handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(handler)
    logger.log(25, '\033[1;31m%s\033[0m: %s' % (obj.node['name'], msg))

class OneToOneNode(BasicNode): # FIIK, but it doesn't work otherwise (desyncs or... something)
    def load(self, data, senderChannel):
        ndata, nself = data['frame_number'], self.frame_number
        if ndata >= nself:
            self.frame_number = ndata
            self.compute(data['vector'])
            if ndata > nself:
                return self.calculatePriority(data['frame_number'], self.frame_number)
        return ACCEPTED

def make_send(sender, incr=True, keys=True):
    def _send(data):
        log(sender, '%s with frame %d' % (data.keys() if keys else data, sender.frame_number))
        sender.sendMessage(data)
        if incr:
            sender.frame_number += 1
    return _send

class TwitterStream(ProducingNode):
    def startProducing(self):
        send = make_send(self)
        class Consumer(TwistedTwitterStream.TweetReceiver):
            def connectionFailed(this, why):
                log(self, 'connection failed (%s)' % why)
            def tweetReceived(this, data):
                if 'delete' not in data:
                    send(dict(tweet=data))
        TwistedTwitterStream.sample(TWITTER_USER, TWITTER_PASSWORD, Consumer())

class SpecificStream(ProducingNode):
    def startProducing(self):
        send = make_send(self)
        class Consumer(TwistedTwitterStream.TweetReceiver):
            def __init__(this, terms, tag):
                this._regex = re.compile('|'.join( x.lower() for x in terms ), re.I)
                this._tag = tag
                TwistedTwitterStream.TweetReceiver.__init__(this)
            def connectionFailed(this, why):
                log(self, 'connection failed (%s)' % why)
            def tweetReceived(this, data):
                if 'delete' not in data and data['user']: # and self.regex.search(data['text']):
                    send(dict(tweet=data, word=this._tag))
        for item in self.node['_topics']:
            TwistedTwitterStream.filter(TWITTER_USER, TWITTER_PASSWORD, Consumer(*item), track=[ x.split(None, 1)[0] for x in item[0] ])

class BlogStream(ProducingNode):
    def __init__(self, router, nodeDict):
        ProducingNode.__init__(self, router, nodeDict)
        from backend.utils import weave_streams, make_tuples
        self.feeds = weave_streams(make_tuples(*pair) for pair in self.node['_blogs'])
    
    def startProducing(self):
        from twisted.internet import reactor
        from twisted.web import client
        from random import random
        import feedparser
        send = make_send(self)
        def read(feed, url, tag):
            try:
                item = next(feed)
            except StopIteration:
                reactor.callLater(random(), get, url, tag)
            else:
                post = SocNOC.process_feed_item(item)
                if isinstance(post, basestring):
                    send(dict(post=post, word=tag))
                reactor.callLater(random(), read, feed, url, tag)
        def get(url, tag):
            ( client.getPage(url)
                    .addCallback(feedparser.parse)
                    .addCallback(lambda feed: iter(feed['items']))
                    .addCallback(read, url, tag)
                    .addErrback(lambda err: get(url, tag)) )
        for feed in self.feeds:
            get(*feed)

class TwitterProcess(OneToOneNode):
    def __init__(self, router, nodeDict):
        OneToOneNode.__init__(self, router, nodeDict)
        self.snoc = SocNOC()
        self.snoc.send = make_send(self)
        if '_categories' in self.node:
            with open('backend/affect.pickle') as affect_file:
                self.snoc.categories = dict(self.node['_categories'], affect=pickle.load(affect_file))
    
    def compute(self, data):
        self.snoc.receive_tweet(**data)

class BlogProcess(OneToOneNode):
    def __init__(self, router, nodeDict):
        OneToOneNode.__init__(self, router, nodeDict)
        self.snoc = SocNOC(k=10, spicefreq=0, cnetfreq=0)
        self.snoc.send = make_send(self)
        if '_categories' in self.node:
            with open('backend/affect.pickle') as affect_file:
                self.snoc.categories = dict(self.node['_categories'], affect=pickle.load(affect_file))
    
    def compute(self, data):
        self.snoc.process_post(**data)

class TwitterSom(OneToOneNode):
    def __init__(self, router, nodeDict):
        OneToOneNode.__init__(self, router, nodeDict)
        from backend.som import SOMBuilder
        self.som = SOMBuilder(k=20, map_size=tuple(self.node['_somsize']))
        self.som.send = make_send(self, incr=False)
    
    def compute(self, data):
        self.som.on_message(data)

class RfbfSom(OneToOneNode):
    def __init__(self, router, nodeDict):
        OneToOneNode.__init__(self, router, nodeDict)
        from backend.somfish import SOMFish
        self.som = SOMFish(self.node['_fixed'], k=10, map_size=tuple(self.node['_somsize']))
        self.som.send = make_send(self, incr=False)
    
    def compute(self, data):
        self.som.on_message(data)

class RfbfVec(OneToOneNode):
    def __init__(self, router, nodeDict):
        OneToOneNode.__init__(self, router, nodeDict)
        self.send = make_send(self, incr=False)
    
    @staticmethod
    def orthogonalize(vec1, vec2):
        return vec2 - vec1 * numpy.vdot(vec1, vec2) / numpy.vdot(vec1, vec1)
    
    @staticmethod
    def unpack(dct):
        ret = {}
        for k, v in dct.items():
            ret[k] = numpy.array(v)[1:]
        return ret
    
    def compute(self, data):
        text = data.get('text', None)
        if text and text[0] != '(':
            categories, concepts = self.unpack(data['categories']), self.unpack(data['concepts'])
            if not all( vec.any() for vec in categories.values() ):
                return # ignore if any are zero vectors
            politics = self.orthogonalize(categories['person'], categories['politics'])
            affect = self.orthogonalize(politics, categories['affect'])
            pnorm, anorm = numpy.linalg.norm(politics), numpy.linalg.norm(affect)
            concepts.pop('empty', None) # ignore 'empty' concept if it exists
            for con, vec in concepts.items():
                vnorm = numpy.linalg.norm(vec)
                self.send({ 'concept' : con,
                            'text'    : text,
                            'size'    : float(numpy.sqrt(numpy.sqrt(vnorm))),
                            'x'       : float(numpy.vdot(politics, vec) / pnorm / vnorm),
                            'y'       : float(numpy.vdot(affect, vec) / anorm / vnorm) })
