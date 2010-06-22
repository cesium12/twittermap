from backend.som import SOMBuilder

def main():
    som = SOMBuilder(k=19, map_size=(100, 80), in_channel='/topic/SocNOC/otherbank', out_channel='/topic/SocNOC/som__other_bank')
    som.start()

if __name__ == '__main__': main()
