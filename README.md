Current status: pre-alpha, conceptual

PyOs is a collection of modules that, when put together, form an "operating
sytem". We're a long way from that goal, but you might find some of the
sub-components generally useful.

>Basically, Python can be seen as a dialect of Lisp with "traditional" syntax
~ [Peter Norvig](https://norvig.com/python-lisp.html)

With that in mind, you can imagine PyOs as a modern lisp-machine OS, running on
top of the linux kernal.

At it's core, PyOs is built on network-transparent shared objects. Of course in
python *everything* is an object, including functions and `await/async` style
generators, so it's not as limiting as you'd think. Imperative, functional, and
asynchronous programming paradigms work fine. We're not java.

 * Pynto

Current Status: pre-alpha, the serializer mostly works! And it should only be
vulnerable to DoS/memory-exhaustion attacks, I'll wait until later to introduce
the remote-execution attacks.

Pynto is the Python Network Transparent Object library. It lets you treat a python
object running in another process, or on another computer, as if it was local.

You may prefer to use rpyc, a more mature alternative. I wrote pynto because
rpyc was hard to use.

 * Un-named UI library

Current Status: Imaginary

A mostly side-effect free UI library inspired by react and imgui. Makes heavy
use of caching. Despite being "immediate mode", is still reasonably efficiant
over the network.

