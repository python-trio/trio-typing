This is a very basic first crack at type hints for trio.
It passes `mypy -p trio` but no other testing has been done yet.
trio.testing is not exposed yet.

mypy can't currently represent the signature of `trio.run()` and similar functions
in a way that preserves the argument types unless you create overloads for each arity.
I decided not to bother with that at this stage.
