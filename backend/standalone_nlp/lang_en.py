import sys, os
import cPickle as pickle
sys.path.insert(0, os.path.dirname(__file__))
en_nl = nltools = pickle.load(open(os.path.join(os.path.dirname(__file__), 'lang_en.pickle')))
