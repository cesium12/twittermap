import tweetstream, re
from twittersuck import settings
from twittersuck.db_password import TWITTER_PASSWORD
from twittersuck.spritzer.models import Tweet
from backend.bankmap import specificNOC

class Stream(object):
    def _process_search(self,terms):
        joinlist = []
        for term in terms:
            if ' ' not in term:
                joinlist.append(term)
            else:
                joinlist.append(term.split(' ')[0])
        outstring = ','.join(joinlist)
        return outstring
        
    def __init__(self, user, password, channel="twitter", filter=None, wl=[]):
        self.regex = re.compile("(" + '|'.join([x.lower() for x in wl]) + ')')
        url_start = "http://stream.twitter.com/1/statuses/filter.json?track="
        self.url = url_start + self._process_search(wl)
        self.terms = wl
        self.stream = tweetstream.ReconnectingTweetStream(user, password, url=self.url)
        channel = "/topic/SocNOC/"+channel
        self.theSnoc = specificNOC(channel)
        self.theSnoc.set_filter(filter)
        
    def on_tweet(self, json):
        Tweet.from_json(json)
        text = json['text']
        if self.regex.search(text.lower()):
          self.theSnoc.receiveTweet(json)
        
    def on_delete(self, json):
        Tweet.handle_delete(json)

    def run(self):
        for tweet in self.stream:
            if tweet.has_key('delete'):
                self.on_delete(tweet)
            else:
                self.on_tweet(tweet)


#spritzer = Stream('r_speer', TWITTER_PASSWORD, url=settings.TWITTER_FEED)

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) == 1:    
        spritzer.run()

    else:
        from csc.divisi.util import get_picklecached_thing
        path = sys.argv[1]
        spritzer.theSnoc = get_picklecached_thing(path, None)
        spritzer.run()
