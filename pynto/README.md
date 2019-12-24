# Pynto
## PYthon Network Transparent Objects

A "remote object" interface inspired by rpyc.

This lets you access a python object running in a different process as if it was
local, and running in your process. This is great for quickly prototyping new
software. A chat server can be as simple as exposing a list object and letting
users append their messages to it.

Right now it's not ready for user-facing software, but it's great for internal
tools and prototyping.

## Not open source

This software is licensed under the BSL, a commercial license, with an additial
usage grant allowing you to use it under the terms of the AGPL. After a release
had been available for 5 years it becomes available under the BSD license.

For practical purposes you can consider it duel licensed under the AGPL and
commercial.

# Examples

```python
#A multiprocessing based solution goes here.
```

# How it works

It's based around the idea that all objects
eventually "boil down" to a simple set of immutable primitives, things like
`int`, `str`, and `bool`. These basic immutable primitives are the only objects
that gets sent over the "network", everything else gets passed as a reference.

Your "network" can be a real network, but it can also be a process's
stdin/stdout, or other more exotic inter-processs-communication methods.


## Components

A `server` manages a number of `connection` objects. A `connection` object is
how your script communicates with a particular remote script.

A `netref` is a transparent object proxy for an object running in a remote script.

 * Server responsibilities

For simple connection types, like `StdStreamConnection` connections, we don't
even really need a server. We can instantiate the connection directly. For more
complicated connections the server is responsible for doing things like
authentication, as well as creating a new connection whenever a remote connects.

 * Connection responsibilities

A connection object is responsible for communicating with a remote script. It's
typically wrapping some kind of communication stream like STDIN/STDOUT, a
socket, or other more-exotic inter-process-communication methods (webrtc? shared
memory?).

It's also responsible for doing reference counting, making sure that an object a
remote script is using doesn't get garbage-collected too early.

 * Netref objects

Netref objects simply forward all their calls to a `connection` instance.

---

## Serialization

We use msgpack to serialize objects. Each object is seperated by a newline
character. There are 6 main types of objects we send.

 * Calls

A call is simply a tuple containing (object referance id, method name, args,
kwargs). We're a (mostly) synchronous protocol, the next object decoded is
presumed to be the response to your call, unless it's a call object.

 * Remote reference

This is simply a wrapper around `int`. It uniquelly identifies an object on a
remote.

 * Actual data

The only actual data we ever send is basic immutable types. Things like ints, strings,
floats, etc.

 * tracebacks

When an error happens, we send the information the client needs to reconstruct
the error and perform basic debugging.

 * Memory free

When a netrefs lifecycle ends we need to let the remote script know we don't
need it to keep holding on to it for us.

## Async support

Python's async/await support is built on top of normal python objects, so even
though our protocol is (mostly) synchronous we get async/await/yield for free.

(We might optimize that by doing some horrible things with callbacks though)

## R&D

Does it make sense to ever have non-synchronous transports? I don't think so as
long as the GIL is still around. We have psudo-async due to our callback
structure, and you could build a fully asynchronous calling system on top of
that, although the overhead would be greator than if we just built with async in
mind from the start.

How about promise pipelining? Avoid round trips by letting remote objects talk
directly to one another?

What about replay attacks? I think that should live in the crypto/server layer,
not in the protocol itself.

What about DoS attacks? Can we make a system that has predictable enough
performance characteristics that we can expose it to the public web? #ToDo, make
sure our serializer handles ~4GB strings in a way that doesn't kill it.

Can we use transcrypt to get this code base running in a web browser?

User-facing software:

We need a good security model. Object-capability based security is great, but we
also need better tools for assessing security, and making sure the system
doesn't leak any un-secured types. Thankfully python has been putting a lot of
effort into type-hinting, and we can use that as the basis for a robust
security-policy assesment tool.

We also need to mitigate resource-exhaustion attacks, although this is a less
pressing concern. For event-loop based APIs, we probably just want to add some
prioritization to our task-queue. It's essentially a co-operative multi-tasking
based "operating system" so this approach should be pretty performant and
reasonable predicatable. Of course
we also need to watch out for other types of resource exhaustion, especially
memory related issues. A lot of this will come down to the individual
developers, but that's always the case. I can think of at least 3 pretty popular
websites that are vulnerable to this type of attack.

We also need good guidelines on caching, and some caching middleware. It gets
complicated when dealing with un-hashable user-session objects. Well I mean if
you're just doing the equivelent of HTTP it's pretty simple, but it's more
complicated for more complicated use-cases, and we can simplify it a great deal.

Longer term:

Can we make it easy to create "decentralized objects" or "smart contract
objects"? Using CRDTs or byzantine-fault-tolerent raft consensus? Can we do that
*without* introducing a whole bunch of overhead? PySyncObj is pretty neat, but
doesn't scale. Still, we'd like to to be not much harder than that.
