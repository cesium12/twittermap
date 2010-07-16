import os, re, itertools
from standalone_nlp.lang_en import en_nl
from csc.divisi.util import get_picklecached_thing
from csc.conceptnet4.analogyspace import conceptnet_2d_from_db

###

cnet = get_picklecached_thing('cnet.pickle.gz', lambda: conceptnet_2d_from_db('en', cutoff=10))
affect = get_picklecached_thing('affectiveWNmatrix.pickle', None)
concepts = set(cnet.label_list(0))

def feature_gen(thing):
    for feature in thing.label_list(1):
        yield feature, thing[:,feature]

def feature_cycle(thing):
    return itertools.cycle(feature_gen(thing))

###

with open(os.path.join(os.path.dirname(__file__), 'badwords.txt')) as badfile:
    badwords = badfile.read().strip().split('\n')

def is_bad_word(word):
    return any( dirty in word for dirty in badwords )

###

def check_concept(concept):
    caps = ''.join( w[0] for w in concept.split() )
    if '@' not in caps and caps.upper() == caps and concept.upper() != concept:
        return True
    normalized = en_nl.normalize(concept)
    return normalized in concepts

def english_window(words, wsize=2):
    words = filter(None, ( re.sub(r"[^A-Za-z0-9' -]", '', w) for w in words ))
    for x in xrange(len(words) - wsize + 1):
        pair = ' '.join(words[x:x+wsize])
        if check_concept(pair):
            norm = en_nl.normalize(pair)
            if norm:
                yield norm

def clean_twitter(phrase):
    # Remove non-ASCII chars, and collapse runs of three or more of the same char.
    phrase = re.sub(r'(.)\1{2,}', r'\1\1', re.sub(r'[^\x00-\x7f]', ' ', phrase))
    # Then do other stuff.
    if is_bad_word(phrase.lower()):
        return
    parts = en_nl.tokenize(phrase).split()
    parts += [ x.lower() for x in english_window(parts) ]
    for part in parts:
        if part.startswith(('#', '@', 'http:')):
            yield part
        elif part.strip() and part != 'rt' and not en_nl.is_stopword(part):
            part = en_nl.normalize(part).strip('-')
            if part.strip():
                yield part

###

def make_tuples(iter1, value2=None):
    # [ foo, bar ], baz => [ ( foo, baz), (bar, baz) ]
    return itertools.izip_longest(iter1, [], fillvalue=value2)

def weave_streams(streams):
    # [ 1, 2, 3, 4 ], 'ab' => [ 1, 'a', 2, 'b', 3, 4 ]
    for step in map(None, *streams):
        for item in step:
            if item is not None:
                yield item

def strip_tags(string):
    # http://stackoverflow.com/questions/1732348#1732454
    return re.sub('<.*?>', '', string)
