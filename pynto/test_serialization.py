from serialization import serializer
import msgpack
import random
import string
random.seed(0)#We don't actually want random test cases
#(See also: reproducable builds)
#but we do want to generate random-ish data.
encode = serializer.encode
decode = serializer.decode


sampleData = [
    1,-1,126,-31,200,-200,5000,-5000,
    "Hello World",
    ''.join(random.choice(string.printable) for i in range(200)),
    ''.join(random.choice(string.printable) for i in range(3000)),
    ''.join(random.choice(string.printable) for i in range(300_000)),
    None,True,False,
    (None,True,False,1,40,40000),
    ("".join(random.choice(string.ascii_letters) for i in range(200)),200,None),
    0.1,
    b"foostr",
    b"\x00"*1024,
    b"\x00"*65_536,
]
sampleData.append(tuple(random.choice(sampleData) for i in range(0,200)))

def print_id_usage():
    colors = ['\033[31m','\033[32m','\033[33m','\033[34m','\033[35m','\033[36m',
              '\033[91m','\033[92m','\033[93m','\033[94m','\033[95m','\033[96m']
    functionColors = {None:"\033[0m",}
    for item in set(serializer._decoders.values()):
        color = colors.pop()
        functionColors[item]=color
        print(color+str(item)+"\033[0m")
    print("Available Ids")
    for i in range(256):
        h = hex(i).ljust(5)
        function = serializer._decoders.get(i,None)
        c = functionColors[function]
        print(c+h+"\033[0m",end="")
    print("\n\n")
print_id_usage()

import traceback
for sample in sampleData:
    e = encode(sample)
    try:
        assert e == msgpack.packb(sample,use_bin_type=True)
        assert sample == decode(e)
    except Exception as exception:
        print("sample        :",sample)
        print("our result    :",decode(e))
        print("msgpack result:",msgpack.unpackb(e,raw=False, use_list=False))
        print("Our bytes      :",e)
        print("Reference Bytes:",msgpack.packb(sample,use_bin_type=True))
        print("Decoder:",decode[e[0]].__name__)
        print("----")
        traceback.print_exc()
#        raise
import time

start = time.monotonic()
for i in range(100):
    d = tuple(map(encode,sampleData))
    f = tuple(map(decode,d))
end = time.monotonic()
print("100 samples:",end-start)
print("average: ",(end-start)/100)

print("brine test ----")
from rpyc.core.brine import dump, load
start = time.monotonic()
for i in range(100):
    d = tuple(map(dump,sampleData))
    f = tuple(map(load,d))
end = time.monotonic()
print("100 samples:",end-start)
print("average: ",(end-start)/100)

print("msgpack test ---")
start = time.monotonic()
for i in range(100):
    d = tuple(map(msgpack.packb,sampleData))
    f = tuple(map(msgpack.unpackb,d))
end = time.monotonic()
print("100 samples:",end-start)
print("average: ",(end-start)/100)
