import numpy as np

class RedFishBlueFishSOM(SOMBuilder):
    def handle_vector(self, vec, text):
        if text == u'#democrat' or text.endswith(u'-#republican'):
            self.handle_fixed_vector(vec, text, -1, -1)
        elif text == u'#republican' or text.endswith(u'-#democrat'):
            self.handle_fixed_vector(vec, text, 1, 1)
        SOMBuilder.handle_vector(self, vec, text)
    
def main():
    mapper = RFBFMap(k=9, in_channel='/topic/SocNOC/redfishbluefish',
                     out_channel='/topic/SocNOC/rfbfmap')
    mapper.start()

if __name__ == '__main__': main()
