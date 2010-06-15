from html2text import html2text
from snoc_backend import SocNOC, weave_streams, make_twit_vec
import feedparser
import random
import numpy as np

def category_wingity(socnoc, vec):
    repub = socnoc.ccipca._v[1:, socnoc.ccipca._labels.index('#republican',
    touch=True)]
    dem = socnoc.ccipca._v[1:, socnoc.ccipca._labels.index('#democrat',
    touch=True)]
    total = 0.0
    for (concept,), value in vec.items():
        try:
            concept_idx = socnoc.ccipca._labels.index(concept, touch=False)
        except KeyError:
            continue
        concept_vec = socnoc.ccipca._v[1:, concept_idx]
        concept_mag = np.linalg.norm(concept_vec)
        if concept_mag == 0: continue
        total += value * (np.dot(concept_vec, repub)) / concept_mag
        total -= value * (np.dot(concept_vec, dem)) / concept_mag
    print "Wingity: %4.4f" % total
    return total

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

    socnoc = SocNOC("/topic/SocNOC/redfishbluefish", k=10, spicefreq=None,
    cnetfreq=4)
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
            stop_changing = hash(socnoc.ccipca._v.tostring())
            vec = make_twit_vec(post)
            wingity = category_wingity(socnoc, vec)

            if label == ' #republican -#democrat': target = 1.0
            elif label == ' #democrat -#republican': target = -1.0
            correct = (wingity > 0) == (target > 0)
            print wingity, target, correct
            if correct: score += 1
        
        print "Accuracy for this iteration: %s%%" % (score/len(testing) * 100)
        print >> logfile, "Accuracy for this iteration: %s%%" % (score/len(testing) * 100)
        print
        logfile.flush()
    logfile.close()

test()
