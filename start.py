#!/usr/bin/env python
import sys, socket, IPython.kernel.client
from secrets import MEC_OPTIONS
mec = IPython.kernel.client.MultiEngineClient(*MEC_OPTIONS)
config = dict()
execfile('config', config, config)

tstream = dict(name='stream',  consumesFrom=[],          classType='twitternet.TwitterStream')
sstream = dict(name='stream',  consumesFrom=[],          classType='twitternet.SpecificStream')
bstream = dict(name='stream',  consumesFrom=[],          classType='twitternet.BlogStream')
tproc   = dict(name='process', consumesFrom=['stream'],  classType='twitternet.TwitterProcess')
bproc   = dict(name='process', consumesFrom=['stream'],  classType='twitternet.BlogProcess')
tsom    = dict(name='som',     consumesFrom=['process'], classType='twitternet.TwitterSom', _somsize=config['somsize'])
rsom    = dict(name='som',     consumesFrom=['process'], classType='twitternet.RfbfSom',    _somsize=config['somsize'])
rvec    = dict(name='vec',     consumesFrom=['process'], classType='twitternet.RfbfVec')

localNodes = []
for name in set(sys.argv[1:] or ['twitter']):
    def disamb(node, **kwargs):
        d = lambda s: name + s
        return dict(node, name=d(node['name']), consumesFrom=map(d, node['consumesFrom']), **kwargs)
    if name in config['fishes']:
        info = config['fishes'][name]
        newNodes = [ rvec,    tproc, tstream ]
        if '_blogs' in info:
            newNodes[-2:] = [ bproc, bstream ]
        elif '_topics' in info:
            newNodes[-1:] = [        sstream ]
        localNodes += [ disamb(node, **info) for node in newNodes ]
    elif name in config['twitter']:
        localNodes += [ disamb(tsom), disamb(tproc), disamb(sstream, _topics=config['twitter'][name]) ]
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
