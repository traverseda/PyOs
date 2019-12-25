"""A type-hinted messagepack-like serializer for immutable python types.
Could be extended to a generic type-hinted messagepack serializer without too much trouble.
If you need that, feel free to reach out.

https://github.com/msgpack/msgpack/blob/master/spec.md
"""

#ToDo: Check everything for off-by-one errors

from typing import Union, Tuple, FrozenSet, Iterable, Optional
from typing import get_type_hints

#baseImmutableTypes = Union[str,int,bool,float,bytes,slice,complex,None] #Ellipsis?
#containerImmutableTypes = Union[FrozenSet['containerImmutableTypes'],
#                                Tuple['containerImmutableTypes'],
#                                baseImmutableTypes]

class Serializer:
    def __init__(self):
        self._decoders = dict()
        self._encoders = dict()

    def decode(self, data: bytes, internal=False):
        data, out = self._decoders[data[0]](self, data)
        if internal: return data, out
        return out

    def encode(self, obj):
        out = self._encoders[type(obj)](self, obj)
        return out

    def encode_register(self, func):
        argname, cls = next(iter(get_type_hints(func).items()))
        self._encoders[cls]=func
        return func

    def decode_register(self, keys):
        def wrapper(func):
            if isinstance(keys, int):
                self._decoders[keys]=func
            else:
                for key in keys:
                    self._decoders[key]=func
            return func
        return wrapper

serializer = Serializer()

import struct

@serializer.encode_register
def encode_float(self, obj: float) -> bytes:
    return b'\xcb'+struct.pack("!d", obj)

@serializer.decode_register((202,203))
def decode_float(self, data: bytes) -> Tuple[bytes, float]:
    if data[0]==202: return data[5:], struct.unpack("!l",data[1:5])[0]
    if data[0]==203: return data[9:], struct.unpack("!d",data[1:9])[0]
    raise NotImplementedError

@serializer.encode_register
def encode_bin(self, obj: bytes) -> bytes:
    if len(obj) < 256:
        return b"\xc4"+len(obj).to_bytes(1,byteorder="big")+obj
    elif len(obj) < 65_536:
        return b"\xc5"+len(obj).to_bytes(2,byteorder="big")+obj
    elif len(obj) < 4_294_967_296:
        return b"\xc6"+len(obj).to_bytes(4,byteorder="big")+obj
    raise NotImplementedError("Bytes is too big to encode")

@serializer.decode_register((196,197,198))
def decode_bin(self, data: bytes) -> Tuple[bytes, bytes]:
    if data[0]==196:
        streamLength=data[1]
        data = data[2:]
    if data[0]==197:
        streamLength=int.from_bytes(data[1:3],byteorder="big")
        data = data[3:]
    if data[0]==198:
        streamLength=int.from_bytes(data[1:5],byteorder="big")
        data = data[5:]

    return data[streamLength:], data[:streamLength]
    raise NotImplementedError

@serializer.encode_register
def encode_bool(self, obj: bool) -> bytes:
    if obj: return b'\xc3'
    else: return b'\xc2'

@serializer.decode_register((195,194,192))
def decode_bool_nil(self, data: bytes):
    if data[0] == 195: return data[1:], True
    if data[0] == 194: return data[1:], False
    if data[0] == 192: return data[1:], None

@serializer.encode_register
def encode_tuple(self, obj: tuple) -> bytes:
    if len(obj) < 16:
        b = (144+len(obj)).to_bytes(1,byteorder="big")

    elif len(obj) < 65_536:
        b = b"\xdc"+len(obj).to_bytes(2,byteorder="big")
    elif len(obj) < 4_294_967_295:
        b = b"\xdd"+len(obj).to_bytes(4,byteorder="big")
    else: raise ValueError("Tuple too long")
    for item in obj:
        b+=self.encode(item)
    return b

def decode_tuple_inner(self, data:bytes, arrayLength):
    out=[]
    for i in range(arrayLength):
        data, obj = self.decode(data, internal=True)
        out.append(obj)
    return data, tuple(out)

@serializer.decode_register(range(144,159+1))
def decode_fixtuple(self, data: bytes) -> tuple:
    arrayLength = data[0]-144
    data = data[1:]
    return decode_tuple_inner(self, data,arrayLength)

@serializer.decode_register((220,221))
def decode_tuple(self, data: bytes) -> tuple:
    if data[0] == 220:
        arrayLength = int.from_bytes(data[1:3],byteorder="big")
        data=data[3:]
    elif data[0] == 221:
        arrayLength = int.from_bytes(data[1:5],byteorder="big")
        data=data[5:]
    return decode_tuple_inner(self, data,arrayLength)

@serializer.encode_register
def encode_str(self, obj: str) -> bytes:
    objBytes = obj.encode("utf-8")
    if len(objBytes) < 31: #Fixstring
        typeId = (160+len(objBytes)).to_bytes(1, byteorder='big')
        return typeId+objBytes
    elif len(objBytes) < 255:
        return b'\xd9'+len(objBytes).to_bytes(1,byteorder='big')+objBytes
    elif len(objBytes) < 65536:
        return b'\xda'+len(objBytes).to_bytes(2,byteorder='big')+objBytes
    elif len(objBytes) < 4_294_967_296:
        return b'\xdb'+len(objBytes).to_bytes(4,byteorder='big')+objBytes
    else:
        raise ValueError("Your string is too big to encode.\
        That means it's more than ~4.29GB!\
        That's way too big for this implementation on 2020 hardware.")

@serializer.decode_register(range(160,191+1))
def decode_fixstr(self, data: bytes) -> Tuple[bytes,str]:
    bytesLength = data[0]-160
    data = data[1:]
    return data[bytesLength:], data[:bytesLength].decode("utf-8")

@serializer.decode_register(range(217,219+1))
def decode_str(self, data: bytes) -> Tuple[bytes,str]:
    if data[0]==217: bytesLength=1
    elif data[0]==218: bytesLength=2
    elif data[0]==219: bytesLength=4
    data=data[1:] #Slice off first bit, which tells us how many bytes we use
    # for our string length identifier.
    streamLength = int.from_bytes(data[:bytesLength],byteorder='big')
    data = data[bytesLength:] #Slice off the bytes that tell use how long 
    # the unicode data is.
    return data[streamLength:], data[:streamLength].decode("utf-8")

@serializer.encode_register
def encode_none(self, obj: None) -> bytes:
    return b'\xc0'

@serializer.encode_register
def encode_int(self, obj: int) -> bytes:
    if 128 > obj > -1: #positive fixint
        return obj.to_bytes(1,byteorder='big')
    elif 0 > obj > -33: #negative fixint
        return (256+obj).to_bytes(1,byteorder='big')
    elif 256 > obj > -1: #uint8
        return b"\xcc"+obj.to_bytes(1,byteorder='big')
    elif 65_537 > obj > -1: #uint16
        return b"\xcd"+obj.to_bytes(2,byteorder='big')
    elif 4_294_967_295 > obj > -1: #uint32
        return b"\xce"+obj.to_bytes(4,byteorder='big')
    elif 18_446_744_073_709_551_615 > obj > -1: #uint64
        return b"\xcf"+obj.to_bytes(8,byteorder='big')
    elif 0 > obj > -129: #signed int8
        return b"\xd0"+obj.to_bytes(1,byteorder='big',signed=True)
    elif -128 > obj > -32_769: #signed int16
        return b"\xd1"+obj.to_bytes(2,byteorder='big',signed=True)
    elif -32_768 > obj > -2_147_483_649: #signed int32
        return b"\xd2"+obj.to_bytes(4,byteorder='big',signed=True)
    elif -2_147_483_648 > obj > -9_223_372_036_854_775_808: #signed int64
        return b"\xd3"+obj.to_bytes(8,byteorder='big',signed=True)

    raise ValueError("Integer is not encodable: "+str(obj))

@serializer.decode_register(range(0,127+1))
def decode_fixint(self, data: bytes) -> Tuple[bytes, int]:
    return data[1:], data[0]
@serializer.decode_register(range(224,256))
def decode_neg_fixint(self, data: bytes) -> Tuple[bytes, int]:
    return data[1:], data[0]-256

@serializer.decode_register(range(204,209))
def decode_uint(self, data: bytes) -> Tuple[bytes, int]:
    bytesLength = data[0]-203
    data = data[1:]
    return data[bytesLength:], int.from_bytes(data[:bytesLength],byteorder="big")
@serializer.decode_register(range(208,212))
def decode_int(self, data: bytes) -> Tuple[bytes, int]:
    bytesLength = data[0]-207
    data = data[1:]
    return data[bytesLength:], int.from_bytes(data[:bytesLength],byteorder="big",signed=True)
