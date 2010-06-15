from html2text import html2text
from snoc_backend import SocNOC, weave_streams, make_twit_vec
import feedparser
import random
import numpy as np

def test():
    dfile, rfile = ('./dems.txt', './repubs.txt')

    rstream = open(rfile, 'r')
    rblogs = [x.replace('\n', ' ').strip() for x in rstream.readlines()]
    rstream.close()
    dstream = open(dfile, 'r')
    dblogs = [x.replace('\n', ' ').strip() for x in dstream.readlines()]
    dstream.close()
    blogs = list(weave_streams([[(x, ' #republican -#democrat') for x in
      rblogs], [(x, ' #democrat -#republican') for x in dblogs]]))

    posts_and_labels = []
    for url, labels in blogs:
        for current in feedparser.parse(url)['items']:
            if current.has_key('content'): text = current.content
            else: text = current.summary
            if isinstance(text, list): text = text[0]
            if isinstance(text, dict): text = text['value']
            post = html2text(text).strip()
            posts_and_labels.append( (post, labels) )

    random.shuffle(posts_and_labels)
    split_point = len(posts_and_labels)/2
    training = posts_and_labels[:10]
    testing = posts_and_labels[split_point:]

    socnoc = SocNOC("/topic/SocNOC/redfishbluefish", k=10)
    logfile = open('testing2.log', 'w')

    for j in xrange(1000):
        print "major iteration #", j
        print >> logfile, "major iteration #", j
        socnoc.process_labeled_posts(training)
        score = 0.0
        print 'testing'
        results = []
        repub = socnoc.ccipca._v[:, socnoc.ccipca._labels.index('#republican',
        touch=True)]
        dem = socnoc.ccipca._v[:, socnoc.ccipca._labels.index('#democrat',
        touch=True)]
        for post, label in testing:
            stop_changing = [hash(socnoc.ccipca._v[i].tostring()) for i in xrange(socnoc.ccipca._v.shape[0])]
            vec = make_twit_vec(post)
            #wingity = category_wingity(socnoc, vec)

            assert stop_changing == [hash(socnoc.ccipca._v[i].tostring()) for i in xrange(socnoc.ccipca._v.shape[0])]
            mags = socnoc.ccipca.iteration(vec)
            assert stop_changing == [hash(socnoc.ccipca._v[i].tostring()) for i in xrange(socnoc.ccipca._v.shape[0])]
            repub = socnoc.ccipca._v[:, socnoc.ccipca._labels.index('#republican',
            touch=False)]
            dem = socnoc.ccipca._v[:, socnoc.ccipca._labels.index('#democrat',
            touch=False)]
            repub = repub[:] / np.linalg.norm(repub)
            dem = dem[:] / np.linalg.norm(dem)
            wingity_vec = repub - dem
            wingity = np.dot(wingity_vec, mags)
            if label == ' #republican -#democrat': target = 1.0
            elif label == ' #democrat -#republican': target = -1.0
            else:
                raise ValueError("What is this label? %r" % label)
            results.append( (wingity, target, post) )
        mean = sum([x[0] for x in results]) / len(results)
        for wingity, target, post in results:
            wingity -= mean
            print (wingity, target)
            if (wingity > 0) == (target > 0): score += 1
        
        print "Accuracy for this iteration: %s%%" % (score/len(testing) * 100)
        print >> logfile, "Accuracy for this iteration: %s%%" % (score/len(testing) * 100)
        print
    logfile.close()

test()
