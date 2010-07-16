import numpy, feedparser, nltk, simplejson
import utils
import basic_stomp as stomp
from html2text import html2text
from django.conf import settings
from csc.divisi.forgetful_ccipca import CCIPCA
from csc.divisi.labeled_view import make_sparse_labeled_tensor
from csc.util.vector import pack64

sent_tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')

def make_twit_vec(text, extras=None):
    tweet_text = list(utils.clean_twitter(text)) or [ 'empty' ]
    twitvec = make_sparse_labeled_tensor(ndim=1)
    for word in tweet_text:
        if word.strip() == '': continue
        if word[0] == '-':
            twitvec[word[1:]] += -1
        else:
            twitvec[word] += 1
    twitvec = twitvec.hat()
    if extras is not None:
        for extra in extras.split():
            if extra[0] == '-':
                twitvec[extra[1:]] = -0.1
            else:
                twitvec[extra] = 0.1
    return twitvec

def twit_gen():
    from twittersuck.spritzer.models import Tweet
    for nextTweet in Tweet.objects.order_by('id').iterator():
        thetext = '@' + nextTweet.user.username + ' ' + nextTweet.text
        twitvec = make_twit_vec(nextTweet.text)
        yield (thetext, twitvec)

class SocNOC(object):
    def __init__(self, channel, trans=1, cnetfreq=2, spicefreq=10, k=20, filters=None):
        self.SocNoc = stomp.Connection(host_and_ports=settings.STOMP_HOSTS, user=settings.STOMP_USERNAME, passcode=settings.STOMP_PASSWORD)
        self.channel = channel
        self.cnetfreq = cnetfreq
        self.filters = filters
        self.touchpoints = []
        self.ccipca = CCIPCA(k, amnesia=2.0, remembrance=1000000.0)
        self.cstream = utils.feature_cycle(utils.cnet)
        self.spice = utils.feature_cycle(utils.affect)
        self.spicefreq = spicefreq
        self.iteration = 0
        self.transfreq = trans
        self.categories = {}
        self.SocNoc.start()
        self.SocNoc.connect()
    
    def sendIdentifier(self, stream):
        stream = stream[0]
        title = stream['title']
        link = stream['link']
        transdict = {'title': title, 'link': link}
        self.send(transdict)
    
    def _process_post(self, post, word=None):
        sents = sent_tokenizer.tokenize(post)
        sentcount = 0
        while sentcount < len(sents):
            if self.cnetfreq and self.iteration % self.cnetfreq == 0:
                thetext, assertion = self.cstream.next()
            elif self.spicefreq and self.iteration % self.spicefreq == 0:
                thetext, assertion = self.spice.next()
            else:
                thetext = sents[sentcount]
                sentcount += 1
                if thetext == '':
                    continue
                assertion = make_twit_vec(thetext, extras=word)
                if assertion is None:
                    continue
                thetext += ' // ' + word
            self.ccipca_iter(assertion, thetext)
    
    def process_labeled_posts(self, posts):
        for p in posts:
            self._process_post(*p)
    
    def _process_feed_item(self, current, word=None):
        self.sendIdentifier((current, word))
        if current.has_key('content'):
            text = current.content
        else:
            text = current.summary
        if isinstance(text, list):
            text = text[0]
        if isinstance(text, dict):
            text = text['value']
        post = html2text(text).strip()
        self._process_post(post, word)
    
    def _process_feed_list(self, feeds):
        return utils.weave_streams(utils.make_tuples(feedparser.parse(x)['items'], y) for (x, y) in feeds)
    
    def process_labeled_RSS_feed(self, feeds):
        for current, word in self._process_feed_list(feeds):
            self._process_feed_item(current, word)
    
    def process_RSS_feed(self, feeds):
        for current, _ in self._process_feed_list(utils.make_tuples(feeds)):
            self._process_feed_item(current)
    
    def fromTwitterDB(self, n=None):
        twitter = twit_gen()
        while (n is None or self.iteration < n):
            if self.iteration % self.cnetfreq == 0:
                thetext, assertion = self.cstream.next()
            elif self.iteration % self.spicefreq == 0:
                thetext, assertion = self.spice.next()
            else:
                thetext, assertion = twitter.next()
                if assertion is None: continue
            self.ccipca_iter(assertion, thetext)
    
    def receiveTweet(self, tweetdict):
        user = '@' + tweetdict['user']['screen_name']
        text = user + ' ' + utils.strip_tags(tweetdict['text'])
        if self.filters and not any( filt in text.lower() for filt in self.filters ):
            return
        if self.iteration % self.spicefreq == 0:
            thetext, assertion = self.spice.next()
            self.ccipca_iter(assertion, thetext)
        if self.iteration % self.cnetfreq == 0:
            thetext, assertion = self.cstream.next()
            self.ccipca_iter(assertion, thetext)
        assertion = make_twit_vec(text)
        if assertion is not None:
            self.ccipca_iter(assertion, text)
    
    def send(self,data):    
        msg = simplejson.dumps(data)
        self.SocNoc.send(msg, destination=self.channel)
    
    def get_concept_position(self,concept):
        try:
            loc = self.ccipca._labels.index(concept, touch=False)
            return self.ccipca._v[:,loc]  
        except IndexError:
            return None
    
    def ccipca_iter(self, assertion, thetext):
        reconstructed = self.ccipca.iteration(assertion, True)
        thetext = unicode(thetext)
        norms = numpy.sqrt(numpy.sum(self.ccipca._v * self.ccipca._v, axis=1))
        self.iteration += 1
        
        conceptsdict = {}
        for word in assertion.keys():
            word = word[0]
            conceptsdict[word] = pack64(self.get_concept_position(word))
        
#        for concept in self.touchpoints:
#            loc = self.get_concept_position(word)
#            if loc is not None:
#                conceptsdict[concept] = pack64(loc)
        
        if self.iteration % self.transfreq == 0:
            categorydict = {}
            for catname, category in self.categories.items():
                catvec = numpy.zeros(self.ccipca._v.shape[1])
                for entry, value in category.items():
                    if entry in self.ccipca._labels:
                        idx = self.ccipca._labels.index(entry)
                        catvec[idx] = value
                categorydict[catname] = pack64(numpy.dot(catvec,
                self.ccipca._v.T)*norms*norms)
            
            self.send({ 'coordinates' : pack64(reconstructed),
                        'magnitudes' : pack64(list(norms)),
                        'text' : thetext,
                        'concepts' : conceptsdict,
                        'categories': categorydict })

if __name__ == '__main__':
    channel = "/topic/SocNOC/twitter"
    snoc = SocNOC(channel)
    snoc.fromTwitterDB()
