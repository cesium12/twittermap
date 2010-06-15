import numpy as np
from backend.som import SOMBuilder, log

def main():
    som = SOMBuilder(k=19, map_size=(100, 80), in_channel='/topic/SocNOC/bt', out_channel='/topic/SocNOC/som_bt')
    som.start()

if __name__ == '__main__': main()
