import numpy, feedparser, nltk, simplejson, itertools
from csc.divisi.forgetful_ccipca import CCIPCA
from csc.conceptnet4.analogyspace import conceptnet_2d_from_db
import utils

tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
cthing = utils.get_thing('cnet.pickle.gz', lambda: conceptnet_2d_from_db('en', cutoff=10))
athing = utils.get_thing('spice.pickle.gz')
utils.concepts = set(cthing.label_list(0))

class SocNOC(object):
    def __init__(self, transfreq=1, cnetfreq=2, spicefreq=10, k=20, filters=None):
        self.ccipca = CCIPCA(k, amnesia=2.0, remembrance=1000000.0)
        self.filters = filters
        self.iteration = 0
        self.touchpoints = []
        self.categories = {}
        
        self.transfreq = transfreq
        self.cnet = utils.feature_cycle(cthing)
        self.cnetfreq = cnetfreq
        self.spice = utils.feature_cycle(athing)
        self.spicefreq = spicefreq
    
    def process_feed(self, feeds):
        self.process_labeled_feed(utils.make_tuples(feeds, None))
    
    def process_labeled_feed(self, feeds):
        for current, word in self.process_feed_list(feeds):
            self.process_post(self.process_feed_item(current), word)
    
    @staticmethod
    def process_feed_list(feeds):
        return utils.weave_streams(utils.make_tuples(feedparser.parse(x)['items'], y) for (x, y) in feeds)
    
    @staticmethod
    def process_feed_item(current):
        text = current.get('content', current.get('summary', None))
        if text is None:
            return
        if isinstance(text, list):
            text = text[0]
        if isinstance(text, dict):
            text = text['value']
        return utils.strip_tags(text).strip()
    
    def process_post(self, post, word=None):
        for text in tokenizer.tokenize(post):
            if text:
                self.ccipca_iter('%s // %s' % (text, word), text, extras=word)
    
    def receive_tweet(self, tweetdict):
        user = '@' + tweetdict['user']['screen_name']
        text = user + ' ' + utils.strip_tags(tweetdict['text'])
        if not self.filters or any( filt in text.lower() for filt in self.filters ):
            self.ccipca_iter(text, text)
    
    def ccipca_iter(self, text, baretext, extras=None):
        assertion = utils.make_twit_vec(baretext, extras=extras)
        if assertion is not None:
            if self.cnetfreq and self.iteration % self.cnetfreq == 0:
                self._ccipca_iter(*self.cnet.next())
            if self.spicefreq and self.iteration % self.spicefreq == 0:
                self._ccipca_iter(*self.spice.next())
            self._ccipca_iter(text, assertion)
            self.iteration += 1
    
    def _ccipca_iter(self, text, assertion):
        print 'iteration is really', self.iteration, "don't believe the following:",
        reconstructed = self.ccipca.iteration(assertion, True)
        if not ( self.transfreq and self.iteration % self.transfreq == 0 ):
            return
        sqnorm = numpy.sum(self.ccipca._v * self.ccipca._v, axis=1)
        
        concepts = {}
        for word in itertools.chain(( key[0] for key in assertion.keys() ), self.touchpoints):
            try:
                loc = self.ccipca._labels.index(word, touch=False)
                pos = self.ccipca._v[:,loc]
                concepts[word] = list(pos)
            except IndexError:
                pass
        
        categories = {}
        for catname, category in self.categories.items():
            catvec = numpy.zeros(self.ccipca._v.shape[1])
            for entry, value in category.items():
                if entry in self.ccipca._labels:
                    catvec[self.ccipca._labels.index(entry)] = value
            categories[catname] = list(numpy.dot(catvec, self.ccipca._v.T) * sqnorm)
        
        self.send({ 'text' : unicode(text),
                    'coordinates' : list(reconstructed),
                    'magnitudes' : list(numpy.sqrt(sqnorm)),
                    'concepts' : concepts,
                    'categories' : categories })
    
    def send(self, data): # override this method
        print simplejson.dumps(data)
