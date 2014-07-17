

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
       because integers are *opaque* values

    Since a standard C array of booleans would usually be 'char B[n]', this saves 8 times the space. Not that much, but not insignificant either.
    TODO: support bitwise ops, so that all bits can be and, or'd, and xor'd en masse
    """
    def __init__(self, size, wordsize=32):
        # hmmmm how
        self._wordsize = wordsize #TODO: this should come from whatever we feed into self._array; for now we hardcode
        # find
        # Note: relies on the wordsize being a power of 2!!
        self._addrbits = 0
        self._addrmask = wordsize - 1 #if wordsize is a power of 2 (ie 2**k), then one less than it is the number with k 1-bits in a row        
        self._wordmask = (1<<wordsize) - 1 #this is necessary in setitem(). see below.
        
        while wordsize & 1 == 0:
            assert wordsize, "Ran out of wordsize without hitting the end!!"
            wordsize >>= 1
            self._addrbits += 1
        assert wordsize == 1
        
        #print("input:", bin(size)) #DEBUG
        #print("addr:", self._addrbits, bin(self._addrmask)) #DEBUG

        self._size = size #store the original size because it's (wordsize-1)/wordsize times likely that we are not an even multiple and there will be some waste bits which we must make sure to make illegal to access (also, this is slightly faster for very little space)

        a, b = self._addr(size - 1) #-1 because 'size' is not actually a valid storage location, and addr() balks at that now!!
          # This is okay; the pseudo-ceil() line takes care of it. The consequence is that: the only time ceil() doesn't happen is if size is an even multiple of the wordsize *plus one*, but in that case, instead, a will have been rounded up by 1 already.
        #print("ADDRESS:", bin(a), bin(b)) #DEBUG
        if b > 0: a+=1 #ceil() the number of words; if b == 0 then we need *exactly* a<<wordbits cells, but if it's larger then we need one more
        self._array = np.zeros(a, np.int32)

        
        
    def _addr(self, n):
        "map the bit address n to physical address (word, bit)"
        if not (0 <= n < len(self)): raise ValueError(n)
        return (n >> self._addrbits, n & self._addrmask)

    def __getitem__(self, n):
        if isinstance(n, slice):
            return [self[i] for i in range(len(self))[n]]
        a, b = self._addr(n)
        #print("__getitem__; ", "[%d,%d] = " % (a,b), bin(self._array[a])) #DEBUG
        return bool(self._array[a] & (1 << b))
        
    def __setitem__(self, n, v):
        if isinstance(n, slice):
            for i,vv in zip(range(len(self))[n], v):
                self[i] = vv
            return

        if not isinstance(v, bool): raise TypeError
        
        a, b = self._addr(n)
        
        
        # two expressions: | (~(1<<b) & wordmask), but this is awkward because ~ gives a negative number (because of two's complement) and if you want unsigned you must mask
        # or, we can use the fact that xor'ing flips bits:
        # oh snap
        # dammit
        # duh
        # x & 1 = x
        # x & 0 = 0
        if v: #turn on bit b
            # since
            # x | 1 = 1
            # x | 0 = x
            #  the bit we want on, we set to 1 in our mask, and we leave the rest as 0, so then they get passed through
            self._array[a] |= (1<<b)
        else: #turn off
            # since
            # x & 1 = x
            # x & 0 = 0
            #  the bit we want on, we set to 0 in our mask, and make all the rest 1
            #  this is trickier, because two's complement gets in the way:
            #  in python (and signed C integers! see inv.c!) "~x = -(x+1)"
            #  in C, you can just ignore the type with a cast
            #  but in Python, integers are a special type with an infinite number of bits,
            #  so the sign bit is hard to get rid of
            # but we can do it with--go figure--a bit mask, which always gives unsigned values, in Python
            # This is the only place we use _wordmask. We could compute it here, but it's faster to precache it.
            
            self._array[a] &= (~(1 << b) & self._wordmask)
        
        #print("__setitem__; ", "[%d,%d] = " % (a,b), bin(self._array[a])) #DEBUG

    def __len__(self):
        return self._size        

def test():
    import random
    def pad_bin(x, pad=8):
        " a version of bin() which pads out to a spec; python doesn't have a 'b' character in its formatting strings, so this is the next best thing"
        x = bin(x)[2:]
        x = "0"*(pad - len(x)) + x
        return x
        
    B = Bitmap(int(sys.argv[1]) if len(sys.argv)>1 else 235)
    for i in range(len(B)):
        b = random.choice([True, False])
        B[i] = b
        assert B[i] == b, "Testing __setitem__"
        #print (b, "-->", i, B[i]) #DEBUG

    # extract the raw bytes in the array, map them to bits, and compare with the value of B
    bits = "".join([pad_bin(ord(e))[::-1] for e in B._array.data[:]]) #note: we *reverse* [::-1] so that bit 0 is at position 0, instead of position 7, as it would be written with MSB-at-left notation
    # also, since my machine is an x86_54, it's little-endian, so numpy's array is laid out least significant bytes in each array entry *first*; if this was not true, we would also need to reverse every word's bytes
    bits = [bool(int(e)) for e in bits]
    V = B[:]
    #print(V)
    fails = [i for i,(v,b) in enumerate(zip(V, bits)) if v != b]
    assert not fails

    print("tests passed")
    


if __name__ == '__main__':
    test()
