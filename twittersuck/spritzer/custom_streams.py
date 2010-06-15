from twittersuck import settings
from twittersuck.db_password import TWITTER_PASSWORD
from twittersuck.spritzer.stream import Stream

tech = Stream('alex_the_cat', TWITTER_PASSWORD,
url='http://stream.twitter.com/1/statuses/filter.json?track=bestbuy,twelpforce,geeksquad,laptop,iphone,android,windows,linux,mac,leopard,ubuntu,python,ruby,java,django,rails,lappy,netbook,pc,webcam,google,ipad', channel="tech")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) == 1:    
        tech.run()

    else:
        from csc.divisi.util import get_picklecached_thing
        path = sys.argv[1]
        tech.theSnoc = get_picklecached_thing(path, None)
        tech.run()

