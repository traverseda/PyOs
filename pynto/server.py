"""
"""
import asyncio
import collections
import logging
from serialization import remoteCall

log = logging.getLogger("pynto")

class IdentityDict(dict):
    """A bi-directional dictionary"""
    def __init__(self, *args, **kwargs):
        super(bidict, self).__init__(*args, **kwargs)
        self.inverse = {}
        for key, value in self.items():
            self.inverse.setdefault(value,[]).append(key)

    def __setitem__(self, key, value):
        if key in self:
            self.inverse[self[key]].remove(key)
        super(bidict, self).__setitem__(key, value)
        self.inverse.setdefault(value,[]).append(key)

    def __delitem__(self, key):
        self.inverse.setdefault(self[key],[]).remove(key)
        if self[key] in self.inverse and not self.inverse[self[key]]:
            del self.inverse[self[key]]
        super(bidict, self).__delitem__(key)

from serializer import MessagePackSerializer

class Connection(MessagePackSerializer):
    """A connection to a remote server. Generally one of these
    exists for each process you might want to talk to.
    """
    def __init__(self, initial=None):
        self.remote_refcount = collections.Counter() #Remote referances to local objects.
        self.object_ids = IdentityDict()

    async def _read_line(self):
        raise NotImplemented

    async def loop(self):
        while True:
            msg = await self._read_line()
            decoded = unpack(msg)
            log.debug(decoded)
            if type(decoded) == remoteCall:
                localObj = self.object_ids[decoded.remoteReference]
                if decoded.method:
                    localObj = getattr(localObj,decoded.method)
                result = localObj(*decoded.args,**decoded.kwargs)

            await asyncio.sleep(self.poll_interval)

    def setup(self):
        return None

import asyncio

class StdStreamConnection(Connection):
    """When you want to connect to a process over it's stdin/stdout
    streams.
    """
    def __init__(self,localOutput,remoteOutput):
        super().__init__()
        self.localOutput=localOutput
        self.remoteOutput=remoteOutput

