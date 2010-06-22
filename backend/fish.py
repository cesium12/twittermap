from snoc_backend import SocNOC, weave_streams
from affect_values import affect

class redfishbluefish(object):
    def __init__(self, dfile, rfile):
        self.both = SocNOC("/topic/SocNOC/redfishbluefish", k=10, spicefreq=0,
        cnetfreq=0)
        self.both.categories = {
            'affect': affect,
            'politics': {'#republican': 1, '#democrat': -1},
            'person': {'person': 1}
        }
        rstream = open(rfile, 'r')
        self.rblogs = [x.replace('\n', ' ').strip() for x in rstream.readlines()]
        rstream.close()
        dstream = open(dfile, 'r')
        self.dblogs = [x.replace('\n', ' ').strip() for x in dstream.readlines()]
        self.touchpoints = []
        dstream.close()
        
    def rfbf(self):
        blogs = list(weave_streams([[(x, ' #republican -#democrat') for x in self.rblogs], [(x, ' #democrat -#republican') for x in self.dblogs]]))
#        blogs = list(weave_streams([[(x, '') for x in self.rblogs], [(x, '') for x in self.dblogs]]))
#        blogs = list(weave_streams([self.rblogs, self.dblogs]))
        self.both.touchpoints = self.touchpoints
#        self.both.process_RSS_feed(blogs)
        self.both.process_labeled_RSS_feed(blogs)

 
            
if __name__ == '__main__':
    rfbf = redfishbluefish('./backend/dems.txt', './backend/repubs.txt')
    while True:
        rfbf.rfbf()
