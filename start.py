#!/usr/bin/env python
import sys, socket, IPython.kernel.client
from secrets import MEC_OPTIONS
mec = IPython.kernel.client.MultiEngineClient(*MEC_OPTIONS)
config = dict()
execfile('config', config, config)

tstream = dict(name='stream',  consumesFrom=None,        classType='twitternet.TwitterStream')
sstream = dict(name='stream',  consumesFrom=None,        classType='twitternet.SpecificStream') # topics
bstream = dict(name='stream',  consumesFrom=None,        classType='twitternet.BlogStream') # blogs
tproc   = dict(name='process', consumesFrom=['stream'],  classType='twitternet.TwitterProcess')
bproc   = dict(name='process', consumesFrom=['stream'],  classType='twitternet.BlogProcess') # categories
tsom    = dict(name='som',     consumesFrom=['process'], classType='twitternet.TwitterSom')
rsom    = dict(name='som',     consumesFrom=['process'], classType='twitternet.RfbfSom') # fixed
rvec    = dict(name='vec',     consumesFrom=['process'], classType='twitternet.RfbfVec')

localNodes = []
for i, name in enumerate(sys.argv[1:] or [None]):
    def disamb(node, **kwargs):
        d = lambda s: s + str(i)
        return dict(node, name=d(node['name']), consumesFrom=map(d, node['consumesFrom'] or []) or None, **kwargs)
    if name in config['fishes']:
        info = config['fishes'][name]
        if 'blogs' in info:
            localNodes += [ disamb(rvec), disamb(rsom, **info), disamb(bproc, **info), disamb(bstream, **info) ]
        elif 'topics' in info:
            localNodes += [ disamb(rvec), disamb(rsom, **info), disamb(tproc), disamb(sstream, **info) ]
        else:
            localNodes += [ disamb(rvec), disamb(rsom, **info), disamb(tproc), disamb(tstream) ]
    elif name in config['twitter']:
        localNodes += [ disamb(tsom), disamb(tproc), disamb(sstream, topics=config['twitter'][name]) ]
    else:
        localNodes += [ disamb(tsom), disamb(tproc), disamb(tstream) ]

graph = {
    socket.gethostname() : {
        'tags' : ['twittermap'],
        'localNodes' : localNodes
    }
}
mec.activate()
mec.push(dict(graph=graph))
mec.execute('import os, vectornet.router')
mec.execute("os.environ['DJANGO_SETTINGS_MODULE'] = 'vectornet.settings'")
mec.execute('vectornet.router.startNetwork(graph)')
