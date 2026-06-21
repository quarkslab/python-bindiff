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

The python module requires Bindiff. Thus first refers to [Zynamics installation directives](https://www.zynamics.com/software.html).

Then the python module can be installed with: 

    pip install python-bindiff

The python module needs to execute the `differ` executable. As such it should be available:
* either in the path
* or via the ``BINDIFF_PATH`` environment variable


Usage as a python module
------------------------

The simplest way to get the programs, already exported with BinExport, diffed, is:

```python
from bindiff import BinDiff

diff = BinDiff.from_binary_files("sample1.exe", "sample2.exe", "out.BinDiff")

# or performing the diff on BinExport files
diff = BinDiff.from_binexport_files("sample1.BinExport", "sample2.BinExport", "out.BinDiff")
```

To load the diffing results of an **existing** diff.BinDiff file, do:

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


Usage as a command line
-----------------------

The ``bindiffer`` command line allows to generate a diff file from the two
.BinExport files or directly from the binaries (thanks to python-binexport and
idascript). The help message is the following:
    
    Usage: bindiffer [OPTIONS] <primary file|dir> <secondary file|dir>

      bindiffer is a very simple utility to diff two binary files using BinDiff in command line. The two input files can be either binary files (in which
      case IDA is used) or directly .BinExport file (solely BinDiff is used). It also accept two directories two diff each files based on their names 

    Options:
      -d, --disassembler [ida|ghidra|binary_ninja]
                                      Disassembler to use
      --disass-path TEXT              Path of the disassembler (dir or binary for IDA, dir for Ghidra)(if not provided search $PATH or environment
                                      variable IDA_PATH, GHIDRA_PATH)
      -t, --threads INTEGER           Thread number to use
      --timeout INTEGER               Per-file export timeout in seconds (if not set, no timeout is enforced)
      -b, --bindiff-path PATH         BinDiff differ directory
      --stop-on-error                 Stop on error
      -o, --output PATH               Output BinDiff file, or directory for batch
      --override                      Override existing output files (includes .BinExport files)
      -bw, --bindiff-workspace PATH   Create a BinDiff Workspace database
      -h, --help                      Show this message and exit.

To work bindiff ``differ`` binary should be in the ``$PATH``, given via
the ``BINDIFF_PATH`` environment variable or with the ``-b`` command option.
Similarly when diff binaries directly the ida64 binary should be available
in the $PATH, given with the ``IDA_PATH`` environment variable or via the
``-i`` command option.
