import sqlite3
import logging
from bindiff import BINDIFF_BINARY
from bindiff.types import ProgramBinDiff, FunctionBinDiff, BasicBlockBinDiff, InstructionBinDiff
from bindiff.types import BasicBlockAlgorithm, FunctionAlgorithm
from binexport import ProgramBinExport
from typing import Union
import subprocess
import tempfile
import os
from pathlib import Path
import shutil
from datetime import datetime


class BinDiff:
    def __init__(self, primary: Union[ProgramBinExport, str], secondary: Union[ProgramBinExport, str], diff_file: str):
        self.primary = ProgramBinExport(primary) if isinstance(primary, str) else primary
        self.secondary = ProgramBinExport(secondary) if isinstance(secondary, str) else secondary
        self._convert_program_classes(self.primary)
        self._convert_program_classes(self.secondary)
        self.similarity = None
        self.confidence = None
        self.version = None
        self.created = None
        self.modified = None

        conn = sqlite3.connect(diff_file)
        self._load_metadata(conn.cursor())
        # also set the similarity/confidence in case the user want to drop the BinDiff object
        self.primary.similarity, self.secondary.similarity = self.similarity, self.similarity
        self.primary.confidence, self.secondary.confidence = self.confidence, self.confidence

        query = "SELECT id, address1, address2, similarity, confidence, algorithm FROM function"
        for f_data in conn.execute(query):
            self._load_function_info(conn.cursor(), *f_data)
        conn.close()

    def _convert_program_classes(self, p):
        p.__class__ = ProgramBinDiff
        for f in p.values():
            f.__class__ = FunctionBinDiff
            for bb in f.values():
                bb.__class__ = BasicBlockBinDiff
                for i in bb.values():
                    i.__class__ = InstructionBinDiff

    def _load_metadata(self, cursor):
        query = "SELECT created, modified, similarity, confidence FROM metadata"
        self.created, self.modified, self.similarity, self.confidence = cursor.execute(query).fetchone()
        self.created = datetime.strptime(self.created, "%Y-%m-%d %H:%M:%S")
        self.modified = datetime.strptime(self.modified, "%Y-%m-%d %H:%M:%S")
        self.similarity = float("{0:.3f}".format(self.similarity))  # round the value to 3 decimals
        self.confidence = float("{0:.3f}".format(self.confidence))  # round the value to 3 decimals

    def _load_function_info(self, conn, f_id, addr1, addr2, similarity, confidence, algo) -> None:
        f1 = self.primary[addr1]
        f2 = self.secondary[addr2]
        f1.similarity, f2.similarity = similarity, similarity
        f1.confidence, f2.confidence = confidence, confidence
        f1.algorithm, f2.algorithm = FunctionAlgorithm(algo), FunctionAlgorithm(algo)
        f1.match, f2.match = f2, f1
        query = "SELECT id, address1, address2, algorithm FROM basicblock WHERE basicblock.functionid == %d" % f_id
        for bb_data in conn.execute(query):
            self._load_basic_block_info(conn, f1, f2, *bb_data)

    def _load_basic_block_info(self, conn, f1, f2, bb_id, bb_addr1, bb_addr2, algo):
        query = "SELECT address1, address2 FROM instruction WHERE instruction.basicblockid == %d" % bb_id
        inst_data = conn.execute(query).fetchall()
        while inst_data:
            bb1, bb2 = f1[bb_addr1], f2[bb_addr2]
            bb1.match, bb2.match = bb2, bb1
            bb1.algorithm, bb2.algorithm = BasicBlockAlgorithm(algo), BasicBlockAlgorithm(algo)
            while inst_data:
                i_addr1, i_addr2 = inst_data[0]
                try:
                    self._load_instruction_info(bb1[i_addr1], bb2[i_addr2])
                    inst_data.pop(0)
                except KeyError as e:
                    bb_addr1, bb_addr2 = inst_data[0]
                    break

    def _load_instruction_info(self, inst1, inst2):
        inst1.match, inst2.match = inst2, inst1

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
