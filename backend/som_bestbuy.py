from backend.som import SOMBuilder

def main():
    som = SOMBuilder(k=19, map_size=(100, 80), in_channel='/topic/SocNOC/bestbuy', out_channel='/topic/SocNOC/som_bestbuy')
    som.start()

if __name__ == '__main__': main()
