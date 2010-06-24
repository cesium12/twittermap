import sys, socket
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

som =     dict(name='som',     consumesFrom=['process'], classType='twitternet.TwitterSom')
process = dict(name='process', consumesFrom=['stream'],  classType='twitternet.TwitterProcess')
stream =  dict(name='stream',  consumesFrom=None,        classType='twitternet.TwitterStream')
sstream = dict(name='stream',  consumesFrom=None,        classType='twitternet.TwitterSpecificStream')
somfish = dict(name='somfish', consumesFrom=['fish'],    classType='twitternet.RfbfSom')
fish =    dict(name='fish',    consumesFrom=None,        classType='twitternet.RfbfStream')

try:
    name = sys.argv[1]
    if name == 'rfbf':
        localNodes = [ dict(somfish), dict(fish, rfile='backend/repubs.txt', dfile='backend/dems.txt') ]
    else:
        localNodes = [ dict(som), dict(process), dict(sstream, wl=specific[name]) ]
except LookupError:
    localNodes = [ dict(som), dict(process), dict(stream) ]

graph = {
    socket.gethostname() : {
        'tags' : ['twittermap'],
        'localNodes' : localNodes
    }
}
mec.push({'g' : graph})
