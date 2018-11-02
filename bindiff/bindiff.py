#from __future__ import annotations  #put it back when python 3.7 will be widely adopted
from __future__ import absolute_import
import os
import sqlite3
import logging
import shutil
from datetime import datetime
import subprocess
import tempfile
from pathlib import Path
from typing import Union, Optional

from binexport import ProgramBinExport

from bindiff import BINDIFF_BINARY
from bindiff.types import ProgramBinDiff, FunctionBinDiff, BasicBlockBinDiff, InstructionBinDiff
from bindiff.types import BasicBlockAlgorithm, FunctionAlgorithm


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
        self.single_match = []

        conn = sqlite3.connect(diff_file)
        self._load_metadata(conn.cursor())
        # also set the similarity/confidence in case the user want to drop the BinDiff object
        self.primary.similarity, self.secondary.similarity = self.similarity, self.similarity
        self.primary.confidence, self.secondary.confidence = self.confidence, self.confidence

        query = "SELECT id, address1, address2, similarity, confidence, algorithm FROM function WHERE 144 <= id <= 116"  # WHERE address1 == 4218784"
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
        alls = conn.execute(query).fetchall()
        #print("f1: 0x%x, f2: 0x%x (id:%d)" % (f1.addr, f2.addr, f_id))
        for bb_data in alls:
            self._load_basic_block_info(conn, f1, f2, *bb_data)

    def _load_basic_block_info(self, conn, f1, f2, bb_id, bb_addr1, bb_addr2, algo):
        #print("bbid:%d bb_addr1:0x%x bb_addr:0x%x" % (bb_id, bb_addr1, bb_addr2))
        query = "SELECT address1, address2 FROM instruction WHERE instruction.basicblockid == %d" % bb_id
        inst_data = conn.execute(query).fetchall()
        while inst_data:
            bb1, bb2 = f1[bb_addr1], f2[bb_addr2]
            if bb1.match or bb2.match:
                if bb1.match != bb2 or bb2.match != bb1:
                    print("Will make a basic block to match another one: (0x%x-0x%x) (0x%x-0x%x)" % (bb1.addr, bb1.match.addr, bb2.addr, bb2.match.addr))
            bb1.match, bb2.match = bb2, bb1
            bb1.algorithm, bb2.algorithm = BasicBlockAlgorithm(algo), BasicBlockAlgorithm(algo)
            while inst_data:
                i_addr1, i_addr2 = inst_data.pop(0)
                try:
                    self._load_instruction_info(bb1[i_addr1], bb2[i_addr2])
                except KeyError as e:
                    # Both instruction should be in a new unmatched basic blocks (other make them orphan)
                    if i_addr1 not in bb1 and i_addr2 not in bb2:
                        bb_addr1 = i_addr1 if i_addr1 in f1 else [x.addr for x in f1.values() if i_addr1 in x][0]
                        bb_addr2 = i_addr2 if i_addr2 in f2 else [x.addr for x in f2.values() if i_addr2 in x][0]
                        if f1[bb_addr1].match or f2[bb_addr2].match:
                            print("One of the two block is already matched")
                            self.single_match.append((i_addr1, i_addr2))
                        else:  # else put instructions back in the list
                            inst_data.insert(0, (i_addr1, i_addr2))
                    else:
                        self.single_match.append((i_addr1, i_addr2))
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
    def from_binary_files(p1_path: str, p2_path: str, diff_out: str) -> Optional['BinDiff']:
        p1 = ProgramBinExport.from_binary_file(p1_path)
        p2 = ProgramBinExport.from_binary_file(p2_path)
        p1_binexport = os.path.splitext(p1_path)[0]+".BinExport"
        p2_binexport = os.path.splitext(p2_path)[0]+".BinExport"
        if p1 and p2:
            retcode = BinDiff._start_diffing(p1_binexport, p2_binexport, diff_out)
            return BinDiff(p1, p2, diff_out) if retcode == 0 else None
        else:
            logging.error("p1 or p2 could not have been 'binexported'")
            return None

    @staticmethod
    def from_binexport_files(p1_binexport: str, p2_binexport: str, diff_out: str) -> Optional['BinDiff']:
        retcode = BinDiff._start_diffing(p1_binexport, p2_binexport, diff_out)
        return BinDiff(p1_binexport, p2_binexport, diff_out) if retcode == 0 else None
