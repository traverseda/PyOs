"""A type-hinted messagepack-like serializer for immutable python types.
Could be extended to a generic type-hinted messagepack serializer without too much trouble.
If you need that, feel free to reach out.

https://github.com/msgpack/msgpack/blob/master/spec.md
"""

#ToDo: Check everything for off-by-one errors

from typing import Union, Tuple, FrozenSet, Iterable, Optional

#baseImmutableTypes = Union[str,int,bool,float,bytes,slice,complex,None] #Ellipsis?
#containerImmutableTypes = Union[FrozenSet['containerImmutableTypes'],
#                                Tuple['containerImmutableTypes'],
#                                baseImmutableTypes]

from functools import singledispatch

class Decoder(dict):
    def __call__(self, data: bytes, internal=False):
        data, out = self[data[0]](data)
        if internal: return data, out
        return out
    def register(self, keys):
        def wrapper(func):
            if isinstance(keys, int):
                self[keys]=func
            else:
                for key in keys:
                    self[key]=func
            return func
        return wrapper

decode=Decoder()

@singledispatch
def encode(obj) -> bytes:
    raise NotImplementedError("Can't encode object of type "+str(type(obj)))

import struct

@encode.register
def encode_float(obj: float) -> bytes:
    return b'\xcb'+struct.pack("!d", obj)

@decode.register((202,203))
def decode_float(data: bytes) -> Tuple[bytes, float]:
    if data[0]==202: return data[5:], struct.unpack("!l",data[1:5])[0]
    if data[0]==203: return data[9:], struct.unpack("!d",data[1:9])[0]
    raise NotImplementedError

@encode.register
def encode_bin(obj: bytes) -> bytes:
    if len(obj) < 256:
        return b"\xc4"+len(obj).to_bytes(1,byteorder="big")+obj
    elif len(obj) < 65_536:
        return b"\xc5"+len(obj).to_bytes(2,byteorder="big")+obj
    elif len(obj) < 4_294_967_296:
        return b"\xc6"+len(obj).to_bytes(4,byteorder="big")+obj
    raise NotImplementedError("Bytes is too big to encode")

@decode.register((196,197,198))
def decode_bin(data: bytes) -> Tuple[bytes, bytes]:
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

@encode.register
def encode_bool(obj: bool) -> bytes:
    if obj: return b'\xc3'
    else: return b'\xc2'

@decode.register((195,194,192))
def decode_bool_nil(data: bytes):
    if data[0] == 195: return data[1:], True
    if data[0] == 194: return data[1:], False
    if data[0] == 192: return data[1:], None

@encode.register
def encode_tuple(obj: tuple) -> bytes:
    if len(obj) < 16:
        b = (144+len(obj)).to_bytes(1,byteorder="big")
    elif len(obj) < 65_536:
        b = b"\xdc"+len(obj).to_bytes(2,byteorder="big")
    elif len(obj) < 4_294_967_295:
        b = b"\xdd"+len(obj).to_bytes(4,byteorder="big")
    else: raise ValueError("Tuple too long")
    for item in obj:
        b+=encode(item)
    return b

def decode_tuple_inner(data:bytes, arrayLength):
    out=[]
    for i in range(arrayLength):
        data, obj = decode(data, internal=True)
        out.append(obj)
    return data, tuple(out)

@decode.register(range(144,159+1))
def decode_fixtuple(data: bytes) -> tuple:
    arrayLength = data[0]-144
    data = data[1:]
    return decode_tuple_inner(data,arrayLength)

@decode.register((220,221))
def decode_tuple(data: bytes) -> tuple:
    if data[0] == 220:
        arrayLength = int.from_bytes(data[1:3],byteorder="big")
        data=data[3:]
    elif data[0] == 221:
        arrayLength = int.from_bytes(data[1:5],byteorder="big")
        data=data[5:]
    return decode_tuple_inner(data,arrayLength)

@encode.register
def encode_str(obj: str) -> bytes:
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

@decode.register(range(160,191+1))
def decode_fixstr(data: bytes) -> Tuple[bytes,str]:
    bytesLength = data[0]-160
    data = data[1:]
    return data[bytesLength:], data[:bytesLength].decode("utf-8")

@decode.register(range(217,219+1))
def decode_str(data: bytes) -> Tuple[bytes,str]:
    if data[0]==217: bytesLength=1
    elif data[0]==218: bytesLength=2
    elif data[0]==219: bytesLength=4
    data=data[1:] #Slice off first bit, which tells us how many bytes we use
    # for our string length identifier.
    streamLength = int.from_bytes(data[:bytesLength],byteorder='big')
    data = data[bytesLength:] #Slice off the bytes that tell use how long 
    # the unicode data is.
    return data[streamLength:], data[:streamLength].decode("utf-8")

@encode.register
def encode_none(obj: None) -> bytes:
    return b'\xc0'

@encode.register
def encode_int(obj: int) -> bytes:
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

@decode.register(range(0,127+1))
def decode_fixint(data: bytes) -> Tuple[bytes, int]:
    return data[1:], data[0]
@decode.register(range(224,256))
def decode_neg_fixint(data: bytes) -> Tuple[bytes, int]:
    return data[1:], data[0]-256

@decode.register(range(204,209))
def decode_uint(data: bytes) -> Tuple[bytes, int]:
    bytesLength = data[0]-203
    data = data[1:]
    return data[bytesLength:], int.from_bytes(data[:bytesLength],byteorder="big")
@decode.register(range(208,212))
def decode_int(data: bytes) -> Tuple[bytes, int]:
    bytesLength = data[0]-207
    data = data[1:]
    return data[bytesLength:], int.from_bytes(data[:bytesLength],byteorder="big",signed=True)
