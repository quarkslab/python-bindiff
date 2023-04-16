# Python Bindiff

``python-bindiff`` is a python module aiming to give a friendly interface to launch
and manipulate bindiff between two binary iles.

How it works ?
--------------

The module relies on [python-binexport](https://github.com/quarkslab/python-binexport)
to extract programs .BinExport and then directly interact with the binary ``differ``
(of zynamics) to perform the diff. The generated diff file is then correlated
with the two binaries to be able to navigate the changes.

Installation
------------

    pip install python-bindiff


Usage as a python module
------------------------

The simplest way to get the programs diffed is:

```python
from bindiff import BinDiff

diff = BinDiff("sample1.BinExport", "sample2.BinExport", "diff.BinDiff")
print(diff.similarity, diff.confidence)
# do whatever you want with diff.primary, diff.secondary which are the
# two Program object
```

But programs can be instanciated separately:

```python
from binexport import ProgramBinExport
from bindiff import BinDiff
p1 = ProgramBinExport("sample1.BinExport")
p2 = ProgramBinExport("sample2.BinExport")

diff = BinDiff(p1, p2, "diff.BinDiff")
```

**Note that all the diff data are embedded inside program objects thus
after instanciating BinDiff those ``p1`` and ``p2`` are modified.**

From the API it is also possible to directly perform the BinExport
extraction and the diffing:

```python
from bindiff import BinDiff

diff = BinDiff.from_binary_files("sample1.exe", "sample2.exe", "out.BinDiff")

# or performing the diff on BinExport files
diff = BinDiff.from_binexport_files("sample1.BinExport", "sample2.BinExport", "out.BinDiff")
```

Usage as a command line
-----------------------

The ``bindiffer`` command line allows to generate a diff file from the two
.BinExport files or directly from the binaries (thanks to python-binexport and
idascript). The help message is the following:
    
    Usage: bindiffer [OPTIONS] <primary file> <secondary file>
    
      bindiffer is a very simple utility to diff two binary files using BinDiff in command line. The two input files can be either binary files (in which case
      IDA is used) or directly .BinExport file (solely BinDiff is used).
    
    Options:
      -i, --ida-path PATH      IDA Pro installation directory
      -b, --bindiff-path PATH  BinDiff differ directory
      -t, --type <type>        inputs files type ('bin', 'binexport') [default:'bin']
      -o, --output PATH        Output file matching
      -h, --help               Show this message and exit.

To work bindiff ``differ`` binary should be in the ``$PATH``, given via
the ``BINDIFF_PATH`` environment variable or with the ``-b`` command option.
Similarly when diff binaries directly the ida64 binary should be available
in the $PATH, given with the ``IDA_PATH`` environment variable or via the
``-i`` command option.