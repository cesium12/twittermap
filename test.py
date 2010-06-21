from IPython.kernel import client
mec = client.MultiEngineClient()
mec.activate()
print mec.get_ids()

graph = {
    'piffelia': {
        'tags': ['twittermap'],
        'localNodes': [ # may be a race condition if these are in the wrong order
            {
                'name': 'som',
                'consumesFrom': ['process'],
                'classType': 'twitternet.TwitterSom'
            },
            {
                'name': 'process',
                'consumesFrom': ['stream'],
                'classType': 'twitternet.TwitterProcess'
            },
            {
                'name': 'stream',
                'consumesFrom': None,
                'classType': 'twitternet.TwitterStream'
            }
        ]
    }
}
mec.push({'g' : graph})
