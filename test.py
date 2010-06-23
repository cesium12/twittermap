import sys
from IPython.kernel import client
mec = client.MultiEngineClient()
mec.activate()

specific = {
    'bank' : ['bofa', 'bank of america', 'merrill lynch', 'ken lewis', 'brian moynihan', 'greg curl', '%23boa', 'power rewards', 'bankamericard'],
    'otherbank' : ['chase bank', 'jpmorgan', 'jpmorgan chase', 'citi', 'citibank', 'wells', 'wellsfargo', 'gmac', 'hsbc', 'goldman', 'goldman sachs', 'capital one', 'cap one', 'amex', 'american express', 'morgan stanley'],
    'bt' : ['BT Group', 'BT pic', 'British Telecom', 'BT Broadband', 'BT Home hub', 'BTCares', 'Home hub'],
    'gillette' : ['Gillette ProGlide', 'ProGlide'],
    'tech' : ['bestbuy', 'twelpforce', 'geeksquad', 'laptop', 'iphone', 'android', 'windows', 'linux', 'mac', 'leopard', 'ubuntu', 'python', 'ruby', 'java', 'django', 'rails', 'lappy', 'netbook', 'pc', 'webcam', 'google', 'ipad']
}
localNodes = [ # may be a race condition if these are in the wrong order
    {
        'name': 'som',
        'consumesFrom': ['process'],
        'classType': 'twitternet.TwitterSom'
    },
    {
        'name': 'process',
        'consumesFrom': ['stream'],
        'classType': 'twitternet.TwitterProcess'
    }
]
try:
    name = sys.argv[1]
    terms = specific[name]
    localNodes.append({
        'name': 'stream',
        'consumesFrom': None,
        'classType': 'twitternet.TwitterSpecificStream',
        'wl': terms
    })
except LookupError:
    localNodes.append({
        'name': 'stream',
        'consumesFrom': None,
        'classType': 'twitternet.TwitterStream'
    })
graph = {
    'piffelia': {
        'tags': ['twittermap'],
        'localNodes': localNodes
    }
}
mec.push({'g' : graph})
