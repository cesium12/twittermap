import numpy as np
from backend.som import SOMBuilder, log

def main():
    som = SOMBuilder(k=19, map_size=(100, 80), in_channel='/topic/SocNOC/tech', out_channel='/topic/SocNOC/som_tech')
    som.start()

if __name__ == '__main__': main()
