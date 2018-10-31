# Python Bindiff

``python-bindiff`` is a python module aiming to give a friendly interface to launch
and manipulate bindiff between two binary iles.

How it works ?
--------------

The module relies on python-binexport (https://gitlab.qb/rdavid/python-binexport)
to extract programs .BinExport and then directly interact with the binary ``differ``
(of zynamics) to perform the diff. The generated diff file is then correlated
with the two binaries to be able to navigate the changes.

Dependencies
------------

Python bindiff relies on:

* python-binexport (https://gitlab.qb/rdavid/python-binexport)

* click *(for ``bindiffer``)*


Usage as a python module
------------------------



Usage as a command line
-----------------------

