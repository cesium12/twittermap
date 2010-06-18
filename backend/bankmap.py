from snoc_backend import *
from csc.divisi.forgetful_ccipca import CCIPCA
from csc.divisi.labeled_view import make_sparse_labeled_tensor
from twittersuck.spritzer.models import Tweet, strip_tags
from csc.divisi.util import get_picklecached_thing
from csc.conceptnet4.analogyspace import conceptnet_2d_from_db
from itertools import cycle, count
from standalone_nlp.lang_en import en_nl
from django.conf import settings
import numpy, re, feedparser, nltk
import basic_stomp as stomp
import csc.divisi as divisi
from html2text import html2text
import simplejson as json
from csc.util.vector import pack64
from csc.divisi.tensor import data
from badwords import  is_bad_word

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
