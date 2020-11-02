#!/bin/sh
# Please do `brew install zlib` if `pip install pillow` is failing.
# After installing, please set these build flags:
# export CFLAGS=-I/usr/local/opt/zlib/include
# export CPPFLAGS=-I/usr/local/opt/zlib/include
# export LDFLAGS=-L/usr/local/opt/zlib/lib
# If the bundled app doesn't start due to pystray import error, change:
#    return importlib.import_module(__package__ + '._' + module)
# to
#    return importlib.import_module('pystray' + '._' + module)

./setup.py py2app
