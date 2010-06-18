from IPython.kernel import client
mec = client.MultiEngineClient()
mec.activate()
print mec.get_ids()

graph = {
    'piffelia': {
        'tags': ['random_vec'],
        'localNodes': [ # may be a race condition if these are in the wrong order
            {
                'name': 'process',
                'consumesFrom': ['twitter'],
                'classType': 'twitternet.TwitterProcess'
            },
            {
                'name': 'twitter',
                'consumesFrom': None,
                'classType': 'twitternet.TwitterStream'
            }
        ]
    }
}
mec.push({'g' : graph})
