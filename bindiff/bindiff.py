import sqlite3
import logging
from bindiff import BINDIFF_BINARY
from binexport import ProgramBinExport
from typing import Union
import subprocess
import tempfile
import os
from pathlib import Path
import shutil


class BinDiff:
    def __init__(self, primary: Union[ProgramBinExport, str], secondary: Union[ProgramBinExport, str], diff: str):
        pass  # TODO: load the file

    @staticmethod
    def _start_diffing(p1_path: str, p2_path: str, out_diff: str) -> int:
        tmp_dir = Path(tempfile.mkdtemp())
        f1 = Path(p1_path)
        f2 = Path(p2_path)
        cmd_line = [BINDIFF_BINARY.as_posix(), '--primary=%s' % p1_path, '--secondary=%s' % p2_path,
                    '--output_dir=%s' % tmp_dir.as_posix()]
        process = subprocess.Popen(cmd_line, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        retcode = process.wait()
        if retcode != 0:
            logging.error("differ terminated with error code: %d" % retcode)
            return retcode
        # Now look for the generated file
        out_file = tmp_dir / (os.path.splitext(f1.name)[0] + "_vs_" + os.path.splitext(f2.name)[0] + ".BinDiff")
        print(out_file)
        if out_file.exists():
            os.rename(out_file.as_posix(), out_diff)
        else:  # try iterating the directory to find the .BinExport file
            candidates = list(tmp_dir.iterdir())
            if len(candidates) > 1:
                logging.warning("the output directory not meant to contain multiple files")
            found = False
            for file in candidates:
                if os.path.splitext(file.as_posix())[1] == ".BinExport":
                    os.rename(file.as_posix(), out_diff)
                    found = True
                    break
            if not found:
                logging.error("diff file .BinExport not found")
                return -2
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return 0

    @staticmethod
    def from_binary_file(p1, p2, out_diff):
        pass  # TODO: Call the ProgramBinExport.from_binary_file + return an instance of BinDiff

    @staticmethod
    def from_binexport_file(primary, secondary, out_diff):
        pass  # TODO

    def _apply_matching(self):
        pass
        '''
        - add the appropriate attribute and methods the classes
        - iterate the match and apply it to function basic block and instructions
        '''
