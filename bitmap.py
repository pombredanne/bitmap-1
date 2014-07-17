

import sys
import numpy as np



class Bitmap(object): #TODO: subclass from np.array() ?
    """
     Note that there is a weird endianness thing and if you look at the actual layout of bits in memory you might be surprised to see each word
      of your system will make a minor difference which only leaks if you edit _array directly:
      suppose you initialize _array to all 1s (eg. with np.ones); then, only a big-endian (MSB first) machine, B[0] will 1 one, whereas on a little endian machine (LSB first), B[31] will be.
      ..wait, is that true?
      ...hm.
      B[0] is always defined to be (_array[0]&1), so it will be the least significant bit, and if you init with ones(), then.. yes. one is always the least significant bit.
    """
    def __init__(self, size, wordsize=8):
        # hmmmm how
        self._wordsize = wordsize #TODO: this should come from whatever we feed into self._array; for now we hardcode
        # find
        # Note: relies on the wordsize being a power of 2!!
        self._addrbits = 0
        self._addrmask = wordsize - 1 #if wordsize is a power of 2 (ie 2**k), then one less than it is the number with k 1-bits in a row
        self._wordmask = (1 << wordsize) - 1 #same principle, but now we *want* 2**wordsize (== 1<<wordsize) so we can mask out
        
        
        while wordsize & 1 == 0:
            assert wordsize, "Ran out of wordsize without hitting the end!!"
            wordsize >>= 1
            self._addrbits += 1
        assert wordsize == 1
        
        print("input:", bin(size)) #DEBUG
        print("addr:", self._addrbits, bin(self._addrmask)) #DEBUG
        print("wordmask:", bin(self._wordmask))

        self._size = size #store the original size because it's (wordsize-1)/wordsize times likely that we are not an even multiple and there will be some waste bits which we must make sure to make illegal to access (also, this is slightly faster for very little space)

        a, b = self._addr(size - 1) #-1 because 'size' is not actually a valid storage location, and addr() balks at that now!!
          # This is okay; the pseudo-ceil() line takes care of it. The consequence is that: the only time ceil() doesn't happen is if size is an even multiple of the wordsize *plus one*, but in that case, instead, a will have been rounded up by 1 already.
        print("ADDRESS:", bin(a), bin(b)) #DEBUG
        if b > 0: a+=1 #ceil() the number of words; if b == 0 then we need *exactly* a<<wordbits cells, but if it's larger then we need one more
        self._array = np.zeros(a, np.uint32)

        
        
    def _addr(self, n):
        "map the bit address n to physical address (word, bit)"
        if not (0 <= n < len(self)): raise ValueError(n)
        return (n >> self._addrbits, n & self._addrmask)

    def __getitem__(self, n):
        a, b = self._addr(n)
        print("__getitem__; ", "[%d,%d] = " % (a,b), bin(self._array[a]))
        return bool(self._array[a] & (1 << b))
        
    def __setitem__(self, n, v):
        if not isinstance(v, bool): raise TypeError
        a, b = self._addr(n)
        print("__setitem__; ", "[%d,%d] = " % (a,b), bin(self._array[a]))

        #print("\t", bin(~(1 << b)))
        # two expressions: | (~(1<<b) & wordmask), but this is awkward because ~ gives a negative number (because of two's complement) and if you want unsigned you must mask
        # or, we can use the fact that xor'ing flips bits:
        self._array[a] ^= (1 << b)

    def __len__(self):
        return self._size        

def test():
    B = Bitmap(int(sys.argv[1]) if len(sys.argv)>1 else 2352)
    for i in range(len(B)):
        import IPython
        #IPython.embed()
        
        if i % 22 == 0:
            print("setting")
            B[i] = True
        print (i, B[i])


if __name__ == '__main__':
    test()
