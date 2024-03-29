"""bitmap.py

kousu, 2014, 2-clause BSD

[see class Bitmap for documentation]

This was written for my own practice, and is laced through with more comments than necessary, for that purpose. Perhaps someone will find it pedagogical.

TODO:
 - [ ] support bitwise ops, so that all bits can be and, or'd, and xor'd en masse
 - [ ] support more reasonable slicing semantics: actually slice part way (this requires then having an optional .base object and a .offset, as ndarray does) 
 - [ ] support sums (__add__()) and appends (__iadd__() or append()); generally try to make this look as much like a list and not an array as possible.
 - [x] figure out how to read wordsize  whatever we feed into self._array; do the numpy dtypes have a "width" field or something?
   - [ ] weird... np.dtype() and np.int32 (et al.) seem very similar, but one makes objects and the others are types which need to be instantiated before I can query .itemsize. This seems like..cruft. I should go digging.
 - [ ] allow passing a list instead of a size (so Bitmap(5) and Bitmap([False, False, False, False, False]) are identical)
 - Tests:
   - [ ] what happens with different dtypes? what happens with the weird ones like strings? does it just fall over badly?
   - [ ] size = 0
   - [ ] size = 1
   - [ ] size = wordsize
   - [ ] size = very large * wordsize
   - [ ] size = very large
   - [ ]
 - [ ] investigate better integration with np.array(). numpy is fairly flexible about what a, and has a lot of framework in place already. maybe we can define a new np.bool1 dtype?
   - [ ] While I'm at it: It would be nice to support fancy indexing, beyond just slicing.
 - [ ] do profiling and performance testing
   - [ ] does changing the dtype affect speed? how?
 - [ ] implement on ctypes (e.g. define a 'byte' type with bitfields for each entry and use a switch statement (which in python looks like a dictionary lookup or a tedious if-else tree)), which is part of core python, and compare in a) code complexity b) speed
 - [ ] support parallel writes? there might be some use cases for updating , and doing one read-write cycle has got to be better.
 - [ ] implement in cython
"""


"""
Notes
======

Bit Manipulation
----------------

If you are not familiar with bitmaps, you need to know that on all modern machines,
 data can only be manipulated in chunks at a time: bytes (8 bits), words (32 or 64 bits, depending), or larger.
So, to set and unset bits, we need to construct other numbers which we call (bit)masks using shifts and inversions.

Get out your truth tables, and observe that the following equations hold:
 x | 1 = 1
 x | 0 = x
that is, OR'ing with a 1 forces a bit on, and or'ing with a 0 is a no-op (because, logically, A or B is always true if B is true).
So to set a bit we OR with a bitstring that is all 0s except for where we want to set it.

To construct such a string, we can use the shift and or operators: one shift per bit and one or operation to put them all together
e.g. to make a bitstring with only the 7th (NB: counting from 0) bit set, do 1 << 7, which is 0b1 << 7 == 0b10000000

Similarly,
 x & 1 = x
 x & 0 = 0
So to unset a bit we can AND with a string that is all 1s except for 0s where we want the unsetting to happen.

To make such a bitstring, we first make a mirror image bitstring as above and then *invert*:
 ~(1<<7) == ~(0b10000000) == 0b01111111

References:
- https://wiki.python.org/moin/BitwiseOperators
- https://wiki.python.org/moin/BitManipulation

Endianness
-----------
Since numbers are *opaque* values (ie we never interact with their components--
 the bits--directly), the endianness of your machine is not visible to the code below.
 When it does 1<<b, that means it is interacting with the bth least-significant bit,
 and wherever that bit may happen to end up is a hardware implementation detail.
 However, if you look under the hood's hood, at ._array.data[:], and you are using a
 type larger than int8 (bytes are *always* opaque on all modern machines)--say, int32-- 
 you could confusingly see each individual word reversed yet their overall ordering the same.
 That is:
 On a little-endian machine (which you probably are probably reading this on)
       the order of bytes is [ 0, 1, 2, 3 ] [ 4, 5, 6, 7 ] [ 8, 9, 10, 11 ] ....
  but on a big-endian machine,
       the order will be     [ 3, 2, 1, 0 ] [ 7, 6, 5, 4 ] [ 11, 10, 9, 8 ] ....
"""


import numpy as np

class Bitmap(object):
    """
    A packed-boolean array.
    
    A standard C array 'bool B[n]' takes sizeof(bool)*n space, which is usually n bytes, with each byte only ever containing either 0b00000000 or 0b00000001
    This datastructure saves 8 times the space by using each bit available as one storage location.
     
    This behaves like a list [or at least, it will, when it's finished], except that it is strongly-typed so that every value can only be a bool.
    Initializes to all False.
    
    >>> B = Bitmap(66);
    >>> B[5]
    False
    >>> B[7] = B[9] = True
    >>> B[6:12]
    [False, True, False, True, False, False]
    >>> B[17] = 2
    TypeError
    >>> B[99] = True
    IndexError
    """
    def __init__(self, size, dtype=np.int8):
        """
        size: the [currently fixed] size of the array.
        dtype: **THIS SHOULD BE TRANSPARENT AND IRRELEVANT**: optionally, choose which numpy type to use for each word size (ie the bitwidth of each entry in the backing numpy array).
        """
        self._size = size #store the original size because it's (wordsize-1)/wordsize times likely that we are not an even multiple and there will be some waste bits which we must make sure to make illegal to access (also, this is slightly faster for very little space)
        
        # figure out the wordsize based on dtype
        # this is a bit of a hack
        # but nbytes only works(?) on instantiated dtype objects
        # so we initialize one to 0
        wordsize = dtype(0).nbytes * 8 #8 bits in a byte
        #print("Wordsize:", wordsize) #DEBUG
        
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
        if not (0 <= n < len(self)): raise IndexError(n)
        return (n >> self._addrbits, n & self._addrmask)


    def __getitem__(self, n):
        """
        access the nth bit in the bitmap, or a list containing a slice.
        
        returns: a python bool
        """
        if isinstance(n, slice):
            "hobo support for slicing"
            return [self[i] for i in range(len(self))[n]]
            
        a, b = self._addr(n)
        #print("__getitem__; ", "[%d,%d] = " % (a,b), bin(self._array[a])) #DEBUG
        return bool(self._array[a] & (1 << b))
        
    def __setitem__(self, n, v):
        """
        write to the nth bit
        
        v must be a python bool.
        
        Optionally, n can be a slice and v can be an iterable (containing only python bools)
        """
        if isinstance(n, slice):
            "hobo support for slicing"
            for i,vv in zip(range(len(self))[n], v):
                self[i] = vv
            return

        if not isinstance(v, bool): raise TypeError(type(v))
        
        a, b = self._addr(n)        
        
        if v: #turn on bit b
            self._array[a] |= (1<<b)
        else: #turn off bit b
        
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
        "get the current size of the Bitmap"
        return self._size        



def pad_bin(x, pad=8):
    " a version of bin() which pads out to a spec; python doesn't have a 'b' character in its formatting strings, so this is the next best thing"
    x = bin(x)[2:]
    x = "0"*(pad - len(x)) + x
    return x



class NotReached(Exception):
    def __init__(self):
        Exception.__init__(self, "This line should not ever have been reached.")

def test_doc_example():

    B = Bitmap(66);
    assert B[5] == False
    B[7] = B[9] = True
    assert B[6:12] ==  [False, True, False, True, False, False]
    try:
        B[17] = 2
        raise NotReached
    except TypeError:
        pass #good
        
    try:
        B[99] = True
        raise NotReached
    except IndexError:
        pass #good
    
    try:
        B[-9] = True
        raise NotReached
    except IndexError:
        pass #good

def test():
    import sys, random
        
    B = Bitmap(int(sys.argv[1]) if len(sys.argv)>1 else 235)
    print ("There are ", len(B._array), "%s entries backing " % (B._array.dtype.name,), len(B), "bools")
    
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
    
    test_doc_example()
    
    print("tests passed")
    


if __name__ == '__main__':
    test()
