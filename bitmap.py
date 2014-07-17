"""bitmap.py

kousu, 2014, 2-clause BSD

TODO:
 - [ ] support bitwise ops, so that all bits can be and, or'd, and xor'd en masse
 - [ ] support more reasonable slicing semantics: actually slice part way (this requires then having an optional .base object and a .offset, as ndarray does) 
 - [ ] support sums (__add__()) and appends (__iadd__() or append()); generally try to make this look as much like a list and not an array as possible.
 - [x] figure out how to read wordsize  whatever we feed into self._array; do the numpy dtypes have a "width" field or something?
 - Tests:
   - [ ] what happens with different dtypes? what happens with the weird ones like strings? does it just fall over badly?
   - [ ] size = 0
   - [ ] size = 1
   - [ ] size = wordsize
   - [ ] size = very large * wordsize
   - [ ] size = very large
   - [ ]

 - [ ] do profiling
"""




"""
Notes:

Endianness:
Since bytes are *opaque* values (ie we never interact with their components--the bits--directly), endianness
 however, if you look at ._array.data, you might need to be aware of endianness, since 4 ot 8 byte integers are not opaque with regard to their component bytes.
"""


import numpy as np


class Bitmap(object): #TODO: subclass from np.array() ?
    """
    A packed-boolean array.
    
    A standard C array 'bool B[n]' takes sizeof(bool)*n space, which is usually n bytes, with each byte only ever containing either 0b00000000 or 0b00000001
    This datastructure saves 8 times the space
    
    """
    def __init__(self, size, dtype=np.int32):
        
        self._size = size #store the original size because it's (wordsize-1)/wordsize times likely that we are not an even multiple and there will be some waste bits which we must make sure to make illegal to access (also, this is slightly faster for very little space)
        
        # figure out the wordsize based on dtype
        # this is a bit of a hack
        # but nbytes only works(?) on instantiated dtype objects
        # so we initialize one to 0
        wordsize = dtype(0).nbytes * 8 #8 bits in a byte
        #print("Wordsize:", wordsize) #DEBUG
        #print(wordsize - 1)
        

        # precache the mask needed to get the within-word address out of the
        # since wordsize is a power of 2, it has a single bit set at bit location _addrbits
        # so one less than it is the number with _addrbits 1-bits in a row
        self._addrmask = wordsize - 1
        
        # precache the mask needed to make ~ behave itself
        # only used in setitem(). see below.
        # -1 is as before
        self._wordmask = (1<<wordsize) - 1

        # scan wordsize for the location of its MSB
        # NOTE: DESTRUCTIVELY EDITS wordsize!
        self._addrbits = 0
        while wordsize & 1 == 0:
            wordsize >>= 1
            self._addrbits += 1
        assert wordsize > 0, "Wordsize ended up negative somehow. This should be impossible."
        assert wordsize == 1, "Wordsize is supposed to be a power of two, but ran out of wordsize without hitting the end."
                
        #print("input:", bin(size)) #DEBUG
        #print("addr:", self._addrbits, bin(self._addrmask)) #DEBUG

        a, b = self._addr(size - 1) #-1 because 'size' is not actually a valid storage location, and addr() balks at that now!!
        # 
          # This is okay; the pseudo-ceil() line takes care of it. The consequence is that: the only time ceil() doesn't happen is if size is an even multiple of the wordsize *plus one*, but in that case, instead, a will have been rounded up by 1 already.
          # what happens if size == 0!?!
        #print("ADDRESS:", bin(a), bin(b)) #DEBUG
        if b > 0: a+=1 #ceil() the number of words; if b == 0 then we need *exactly* a<<wordbits cells, but if it's larger then we need one more
        self._array = np.zeros(a, dtype)
        
            
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



def pad_bin(x, pad=8):
    " a version of bin() which pads out to a spec; python doesn't have a 'b' character in its formatting strings, so this is the next best thing"
    x = bin(x)[2:]
    x = "0"*(pad - len(x)) + x
    return x


def test():
    import sys, random
    
        
    B = Bitmap(int(sys.argv[1]) if len(sys.argv)>1 else 235)
    expected = []
    for i in range(len(B)):
        b = random.choice([True, False])
        expected.append(b)
        B[i] = b
        assert B[i] == b, "Testing __setitem__"
        #print (b, "-->", i, B[i]) #DEBUG

    # extract the list of booleans in verbose python-boxed objects
    V = B[:]

    # test against expected, to make sure the type is to spec
    assert V == expected
    #fails = [i for i,(v,b) in enumerate(zip(V, expected)) if v != b] #more detailed expression which may aid debugging
    #assert not fails

    # test against the raw bytes in the array, to see that the type is correctly interpreting its backing store
    bits = "".join([pad_bin(ord(e))[::-1] for e in B._array.data[:]]) #note: we *reverse* [::-1] so that bit 0 is at position 0, instead of position 7, as it would be written with MSB-at-left notation
    # also, since my machine is an x86_54, it's little-endian, so numpy's array is laid out least significant bytes in each array entry *first*; if this was not true, we would also need to reverse every word's bytes
    bits = [bool(int(e)) for e in bits]

    #print(V)
    fails = [i for i,(v,b) in enumerate(zip(V, bits)) if v != b]
    assert not fails

    print("tests passed")
    


if __name__ == '__main__':
    test()
