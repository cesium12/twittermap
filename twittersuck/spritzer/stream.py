import tweetstream
from twittersuck import settings
from twittersuck.db_password import TWITTER_PASSWORD
from twittersuck.spritzer.models import Tweet
from backend.snoc_backend import SocNOC

class Stream(object):
    def __init__(self, user, password, url, channel="twitter", filter=None):
        self.stream = tweetstream.ReconnectingTweetStream(user, password, url=url)
        channel = "/topic/SocNOC/"+channel
        self.theSnoc = SocNOC(channel,cnetfreq = 4)
        self.filter = filter
        
    def on_tweet(self, json):
        Tweet.from_json(json)
#        if self.filter:
#            if json['text'].find(self.filter) > -1: self.theSnoc.receiveTweet(json)
#        else:
        self.theSnoc.receiveTweet(json)
        
    def on_delete(self, json):
        Tweet.handle_delete(json)

    def run(self):
        for tweet in self.stream:
            if tweet.has_key('delete'):
                self.on_delete(tweet)
            else:
                self.on_tweet(tweet)


spritzer = Stream('r_speer', TWITTER_PASSWORD, url=settings.TWITTER_FEED)

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) == 1:    
        spritzer.run()

    else:
        from csc.divisi.util import get_picklecached_thing
        path = sys.argv[1]
        spritzer.theSnoc = get_picklecached_thing(path, None)
        spritzer.run()
