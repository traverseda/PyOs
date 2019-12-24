from serialization import encode, decode
import msgpack
import random
import string
random.seed(0)#We don't actually want random test cases
#(See also: reproducable builds)
#but we do want to generate random-ish data.

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
    for item in set(decode.values()):
        color = colors.pop()
        functionColors[item]=color
        print(color+str(item)+"\033[0m")
    print("Available Ids")
    for i in range(256):
        h = hex(i).ljust(5)
        function = decode.get(i,None)
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
