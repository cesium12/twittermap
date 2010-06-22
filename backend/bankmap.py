from snoc_backend import SocNOC, make_twit_vec
from twittersuck.spritzer.models import strip_tags
from csc.divisi.util import get_picklecached_thing
from csc.conceptnet4.analogyspace import conceptnet_2d_from_db
import nltk

sent_tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
cnet = get_picklecached_thing('cnet.pickle.gz', lambda: conceptnet_2d_from_db('en', cutoff=10))
affectivewn = get_picklecached_thing('affectiveWNmatrix.pickle', None)

print "Loading all ConceptNet concepts."
conceptnet_concepts = set(cnet.label_list(0))
    
# Parameters
wsize = 2

class specificNOC(SocNOC):
    def set_filter(self, filters):
        self.filters = filters
    
    def receiveTweet(self, tweetdict):
        user = '@' + tweetdict['user']['screen_name']
        text = user + ' ' + strip_tags(tweetdict['text'])
        if self.filters:
            intweet = False
            for filter in self.filters:
                if text.lower().find(filter) > -1:
                    intweet = True
            if not intweet: return
        if self.iteration % self.spicefreq == 0:
            thetext, assertion = self.spice.next()
            self.ccipca_iter(assertion, thetext)
        if self.iteration % self.cnetfreq == 0:
            thetext, assertion = self.cstream.next()
            self.ccipca_iter(assertion, thetext)
        assertion = make_twit_vec(text)
        if assertion == None: return
        self.ccipca_iter(assertion, text)
