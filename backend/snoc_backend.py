from csc.divisi.forgetful_ccipca import CCIPCA
from csc.divisi.labeled_view import make_sparse_labeled_tensor
from twittersuck.spritzer.models import Tweet, strip_tags
from csc.divisi.util import get_picklecached_thing
from csc.conceptnet4.analogyspace import conceptnet_2d_from_db
import itertools
from standalone_nlp.lang_en import en_nl
from django.conf import settings
import numpy, re, feedparser, nltk
import basic_stomp as stomp
from html2text import html2text
import simplejson as json
from csc.util.vector import pack64

sent_tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
cnet = get_picklecached_thing('cnet.pickle.gz', lambda: conceptnet_2d_from_db('en', cutoff=10))
affectivewn = get_picklecached_thing('affectiveWNmatrix.pickle', None)

print "Loading all ConceptNet concepts."
conceptnet_concepts = set(cnet.label_list(0))
    

# Parameters
wsize = 2


def check_concept(concept):
    ## get capitalized phrases
    caps = ''.join([w[0] for w in concept.split()])
    if '@' not in caps and caps.upper() == caps and concept.upper() != concept: return True
    normalized = en_nl.normalize(concept)
    return normalized in conceptnet_concepts

def is_url(phrase):
    if phrase.startswith('http'): return True
    return False

def english_window(words):
    windows = []
    if words == []: return windows
    words = [q for q in [re.sub(r"[^A-Za-z0-9' -]", '', x) for x in words] if q != '']
    for x in xrange(len(words)-wsize+1):
        pair = " ".join(words[x:x+wsize])
        if check_concept(pair):
            norm = en_nl.normalize(pair)
            windows.append(norm)
            continue
    windows = [w for w in windows if w]
    return windows

def affect_pregen():
    features = affectivewn.label_list(1)
    for feature in features:
        yield feature,affectivewn[:, feature]

def affect_cycler():
    for thing in itertools.cycle(affect_pregen()):
        yield thing

def spice_generator():
    affect = affect_cycler()
    gens = [affect]
    generator_generator = itertools.cycle(gens)
    while True:
        yield generator_generator.next().next()

def cnet_generator():
    features = cnet.label_list(1)
    for feature in features:
        yield feature,cnet[:, feature]

def cnet_cycler():
    for thing in itertools.cycle(cnet_generator()):
        yield thing

def process_word(word):
    word = en_nl.normalize(word)
    return word
        
def cleanTwitterPhrase(phrase):
    #notEnglish = False
    sore = ''
    are = ''
    newphrase = []
    for char in phrase:
        if sore != are or sore != char: 
            if ord(char) >= 128:
                #notEnglish = True
                newphrase.append(' ')
            else:
                newphrase.append(char)
                sore = are
                are = char
    phrase = ''.join(newphrase)
    #if is_bad_word(phrase.lower()): return []
    parts = en_nl.tokenize(phrase).split()
    coll = english_window(parts)
    coll = [x.lower() for x in coll]
    parts += coll
    output = []
    for part in parts:
        if (part.startswith('#') or part.startswith('@') or
        part.startswith('http:')):
            output.append(part)
            continue
        if part == 'rt': continue
        if part == ' ': continue
        if en_nl.is_stopword(part): continue
        part = process_word(part)
        part = part.strip('-')
        if part.strip() == '': continue
        assert part.strip() != ''
        output.append(part)
#    if notEnglish: return []
    return output

tweeterator = Tweet.objects.order_by('id').iterator()
#tweeterator = iter(tweet_cache)

def make_twit_vec(text, extras = None):
    tweet_text = cleanTwitterPhrase(text)
    if tweet_text == []: tweet_text = ['empty']
    twitvec = make_sparse_labeled_tensor(ndim=1)
    for word in tweet_text:
        if word.strip() == '': continue
        if word[0] == '-':
            twitvec[word[1:]] += -1
        else:
            twitvec[word] += 1
    twitvec = twitvec.hat()
    if extras is not None:
        extras = extras.split()
        for extra in extras:
            if extra[0] == '-':
                twitvec[extra[1:]] = -0.1
            else:
                twitvec[extra] = 0.1
    return twitvec

def twit_gen():
    for nextTweet in tweeterator:
        thetext = '@' + nextTweet.user.username + ' ' + nextTweet.text
        twitvec = make_twit_vec(nextTweet.text)
        yield (thetext, twitvec)

def weave_streams(streams):
    '''Repeatedly gets one element from each stream in order until all are exhausted.
    weave_streams([(1,2,3,4), 'ab']) => 1, 'a', 2, 'b', 3, 4'''
    for step in map(None, *streams):
        for item in step:
            if item is not None:
                yield item

def make_tuples(iter1, value2=None):
        # Given [ foo, bar ] and baz, returns [ ( foo, baz), (bar, baz) ]
        return itertools.izip_longest(iter1, [], fillvalue=value2)

def get_feed_items(feeds):
    for (x, y) in feeds:
        try:
            for q in feedparser.parse(x)['items']:
                yield (q, y)
        except LookupError:
            print x, y
            pass

class SocNOC(object):
    def __init__(self, channel, trans =1, cnetfreq =2, spicefreq = 10, k=20):
        self.SocNoc = stomp.Connection(host_and_ports=settings.STOMP_HOSTS, user=settings.STOMP_USERNAME, passcode=settings.STOMP_PASSWORD,)
        self.channel = channel
        self.cnetfreq = cnetfreq
        self.touchpoints = []
        self.filters = None
        # Setup and run ccipca
        self.ccipca = CCIPCA(k, amnesia=2.0, remembrance=1000000.0)
        #self.tweet_cache = Tweet.objects.order_by('id')[:100]
        self.cstream = cnet_cycler()
        self.spice = affect_cycler()
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
        # Takes a list of posts
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
        return weave_streams(make_tuples(feedparser.parse(x)['items'], y) for (x, y) in feeds)
    
    def process_labeled_RSS_feed(self, feeds):
        # Takes a list of Feeds
        for current, word in self._process_feed_list(feeds):
            self._process_feed_item(current, word)
    
    def process_RSS_feed(self, feeds):
        # Takes a list of Feeds
        for current, none in self._process_feed_list(make_tuples(feeds)):
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
        if self.iteration % self.spicefreq == 0:
            thetext, assertion = self.spice.next()
            self.ccipca_iter(assertion, thetext)
        if self.iteration % self.cnetfreq == 0:
            thetext, assertion = self.cstream.next()
            self.ccipca_iter(assertion, thetext)
        user = '@' + tweetdict['user']['screen_name']
        text = user + ' ' + strip_tags(tweetdict['text'])
        assertion = make_twit_vec(text)
        if assertion == None: return
        self.ccipca_iter(assertion, text)
    
    @staticmethod
    def VectortoDict(tensor):
        first = dict(tensor)
        outdict = {}
        for key, value in first.iteritems():
            outdict[key[0]] = value
        return outdict
    
    def send(self,data):    
        msg = json.dumps(data)
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
            
            transdict= {'coordinates': pack64(reconstructed), 'magnitudes':
            pack64(list(norms)), 'text': thetext, 'concepts': conceptsdict,
            'categories': categorydict}
            #print transdict
            self.send(transdict)

if __name__ == '__main__':
    channel = "/topic/SocNOC/twitter"
    snoc = SocNOC(channel)
    snoc.fromTwitterDB()
