

import sys
import numpy as np

class Bitmap(object):
    def __init__(self, size, wordsize=32):
        # hmmmm how
        self._wordsize = wordsize #TODO: this should come from whatever we feed into self._array; for now we hardcode
        # find
        # Note: relies on the wordsize being a power of 2!!
        self._wordbits = 0
        self._wordmask = 1
        self._wordmask = wordsize - 1 #if wordsize is a power of 2 (ie 2**k), then one less than it is the number with k 1-bits in a row
        while wordsize & 1 == 0:
            assert wordsize, "Ran out of wordsize without hitting the end!!"
            wordsize >>= 1
            self._wordbits += 1

        print(bin(size))
        print(self._wordbits, bin(self._wordmask))
        assert wordsize == 1


        a, b = self._addr(size)
        print("ADDRESS:", bin(a), bin(b))
        if b > 0: a+=1 #ceil() the number of words
        self._array = np.zeros(a, np.int32)
        
        
    def _addr(self, n):
        "map the bit address n to physical address (word, bit)"
        return (n >> self._wordbits, n & self._wordmask)



def test():
    B = Bitmap(int(sys.argv[1]) if len(sys.argv)>1 else 2352)

if __name__ == '__main__':
    test()