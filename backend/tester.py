def duplicates(phrase):
    phrase = phrase.lower()
    sore = ''
    are = ''
    newphrase = []
    for char in phrase:
        if sore != are or sore != char: 
            if ord(char) >= 128: newphrase.append(' ')
            newphrase.append(char)
            sore = are
            are = char
            print char, sore, are
            print sore == are and sore == char
    phrase = ''.join(newphrase)
    return phrase

