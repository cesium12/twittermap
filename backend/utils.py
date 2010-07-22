import os, re, itertools, collections, numpy, StringIO
import html5lib
from standalone_nlp.lang_en import en_nl
from csc.divisi.labeled_view import make_sparse_labeled_tensor
from csc.divisi.util import get_picklecached_thing

def local_file(fname):
    return os.path.join(os.path.dirname(__file__), fname)

def get_thing(fname, func=None):
    return get_picklecached_thing(local_file(fname), func)

def feature_gen(thing):
    for feature in thing.label_list(1):
        yield feature, thing[:,feature]

def feature_cycle(thing):
    return itertools.cycle(feature_gen(thing))

###

with open(local_file('badwords.txt')) as badfile:
    badwords = badfile.read().strip().split('\n')

def is_bad_word(word):
    return any( dirty in word for dirty in badwords )

concepts = set()

def english_window(words, wsize=2):
    words = filter(None, ( re.sub(r"[^A-Za-z0-9' -]", '', w) for w in words ))
    for x in xrange(len(words) - wsize + 1):
        pair = ' '.join(words[x:x+wsize])
        caps = ''.join( w[0] for w in pair.split() )
        norm = en_nl.normalize(pair)
        if norm and ( ( '@' not in caps and caps.upper() == caps and pair.upper() != pair ) or norm in concepts ):
            yield norm.lower()

def clean_twitter(phrase):
    phrase = re.sub(r'(.)\1{2,}', r'\1\1', re.sub(r'[^\x00-\x7f]', ' ', phrase))
    if is_bad_word(phrase.lower()):
        return
    parts = en_nl.tokenize(phrase).split()
    for part in itertools.chain(parts, english_window(parts)):
        if part.startswith(('#', '@', 'http:')):
            yield part
        elif part.strip() and part != 'rt' and not en_nl.is_stopword(part):
            part = en_nl.normalize(part).strip('-')
            if part.strip():
                yield part

def make_twit_vec(text, extras=None):
    words = list(clean_twitter(text)) or [ 'empty' ]
    twitvec = make_sparse_labeled_tensor(ndim=1)
    for word in words:
        if word.strip():
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

###

def make_tuples(iter1, value2):
    # [ foo, bar ], baz => [ ( foo, baz), (bar, baz) ]
    return itertools.izip_longest(iter1, (), fillvalue=value2)

def weave_streams(streams):
    # [ 1, 2, 3, 4 ], 'ab' => [ 1, 'a', 2, 'b', 3, 4 ]
    sentinel = object()
    for step in itertools.izip_longest(*streams, fillvalue=sentinel):
        for item in step:
            if item is not sentinel:
                yield item

def strip_tags(html):
    # http://stackoverflow.com/questions/1732348#1732454
    text = StringIO.StringIO()
    stack = collections.deque([ html5lib.parse(html) ])
    while stack:
        node = stack.pop()
        text.write(node.value or '')
        stack.extend(reversed(node.childNodes))
    return text.getvalue()

###

class IMDS:
    def __init__(self, dim, eps=0.01, maxlen=None):
        self.dim = dim
        self.eps = eps
        self.vecsold = collections.deque(maxlen=maxlen)
        self.vecsnew = collections.deque(maxlen=maxlen)
    
    @staticmethod
    def move(placed, new, distance):
        diff = new - placed
        return diff * distance / numpy.linalg.norm(diff) + placed
    
    def dists(self, next):
        for v in self.vecsold:
            yield numpy.linalg.norm(next - v)
    
    def step(self, next):
        num = len(self.vecsold)
        if self.vecsold:
            vec = next[:self.dim]
            while True:
                moved = itertools.imap(self.move, self.vecsnew, itertools.repeat(vec), self.dists(next))
                newvec = sum(moved, numpy.zeros(self.dim)) / num
                if numpy.linalg.norm(newvec - vec) < self.eps:
                    break
                vec = newvec
        else:
            newvec = numpy.zeros(self.dim)
        self.vecsold.append(next)
        self.vecsnew.append(newvec)
        return newvec
