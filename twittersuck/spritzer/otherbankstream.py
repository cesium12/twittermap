from twittersuck import settings
from twittersuck.db_password import TWITTER_PASSWORD
from twittersuck.spritzer.specific_stream import Stream

tech = Stream('r_speer', TWITTER_PASSWORD, channel="otherbank", wl=['chase bank', 'jpmorgan', 'jpmorgan chase', 'citi', 'citibank', 'wells', 'wellsfargo', 'gmac', 'hsbc', 'goldman', 'goldman sachs', 'capital one', 'cap one', 'amex', 'american express', 'morgan stanley'])
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) == 1:    
        tech.run()

    else:
        from csc.divisi.util import get_picklecached_thing
        path = sys.argv[1]
        tech.theSnoc = get_picklecached_thing(path, None)
        tech.run()

