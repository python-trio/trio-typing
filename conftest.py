import sys
if sys.implementation.name == "cpython":
    pytest_plugins = ["trio_typing._tests.datadriven"]
