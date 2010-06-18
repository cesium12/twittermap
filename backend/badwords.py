import os.path
file = open(os.path.join(os.path.dirname(__file__), 'badwords.txt'), 'r')
badwords = [x.replace('\n', "") for x in file.readlines()]
file.close()

def is_bad_word(word):
    for dirty in badwords:
        if dirty in word: return True
    return False
