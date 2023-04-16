from pathlib import Path
from typing import List
import sqlite3
from datetime import datetime
from dataclasses import dataclass
import ctypes

from bindiff.types import FunctionAlgorithm, BasicBlockAlgorithm


@dataclass
class File:
    """
    Represent files parsed
    """

    id: int
    filename: str
    exefilename: str
    hash: str
    functions: int
    libfunctions: int
    calls: int
    basicblocks: int
    libbasicblocks: int
    edges: int
    libedges: int
    instructions: int
    libinstructions: int


@dataclass
class FunctionMatch:
    """
    Class holding a match between two function.
    """

    id: int
    address1: int
    address2: int
    similarity: float
    confidence: float
    algorithm: FunctionAlgorithm


@dataclass
class BasicBlockMatch:
    """
    Class holding a match between two basic blocks
    """

    id: int
    function_match: FunctionMatch
    address1: int
    address2: int
    algorithm: BasicBlockAlgorithm

# @dataclass
# class InstructionMatch:
#     id: int
#     basicblock1: BasicBlockMatch
#     basicblock2: BasicBlockMatch
#     address1: int
#     address2: int


class BindiffFile(object):
    def __init__(self, file: Path | str):
        self._file = file

        # Open database
        conn = sqlite3.connect('file:'+str(file)+'?mode=ro', uri=True)

        # Global variables
        self.similarity = None
        self.confidence = None
        self.version = None
        self.created = None
        self.modified = None
        self._load_metadata(conn.cursor())

        # Files
        self.primary = None
        self.secondary = None
        self._load_file(conn.cursor())

        # Function matches
        self.primary_functions_match = {}
        self.secondary_functions_match = {}
        self._load_function_match(conn.cursor())

        # Basicblock matches
        self.primary_basicblock_match = {}
        self.secondary_basicblock_match = {}
        self._load_basicblock_match(conn.cursor())

        # Instruction matches
        self.primary_instruction_match = {}
        self.secondary_instruction_match = {}
        self._load_instruction_match(conn.cursor())

    @property
    def unmatched_primary_count(self) -> int:
        """
        Returns the number of functions inside primary that are not matched
        """

        return self.primary.functions + self.primary.libfunctions - len(self.primary_functions_match)

    @property
    def unmatched_secondary_count(self) -> int:
        """
        Returns the number of functions inside secondary that are not matched
        """

        return self.secondary.functions + self.secondary.libfunctions - len(self.primary_functions_match)

    @property
    def function_matches(self) -> List[FunctionMatch]:
        """
        Returns the list of matched functions
        """

        return list(self.primary_functions_match.values())

    @property
    def basicblock_matches(self) -> List[BasicBlockMatch]:
        """
        Returns the list of matched basic blocks in primary (and secondary)
        """

        return [x for bb_matches in self.primary_basicblock_match.values() for x in bb_matches.values()]
        # return list(self.primary_basicblock_match.values())

    def _load_file(self, cursor: sqlite3.Cursor) -> None:
        """
        Load diffing file stored in a DB file

        :param cursor: sqlite3 cursor to the DB
        :return: None
        """

        query = "SELECT * FROM file"
        self.primary = File(*cursor.execute(query).fetchone())
        self.secondary = File(*cursor.execute(query).fetchone())

    def _load_metadata(self, cursor: sqlite3.Cursor) -> None:
        """
        Load diffing metadata as stored in the DB file

        :param cursor: sqlite3 cursor to the DB
        :return: None
        """

        query = "SELECT created, modified, similarity, confidence FROM metadata"
        self.created, self.modified, self.similarity, self.confidence = cursor.execute(query).fetchone()
        self.created = datetime.strptime(self.created, "%Y-%m-%d %H:%M:%S")
        self.modified = datetime.strptime(self.modified, "%Y-%m-%d %H:%M:%S")
        self.similarity = float("{0:.3f}".format(self.similarity))  # round the value to 3 decimals
        self.confidence = float("{0:.3f}".format(self.confidence))  # round the value to 3 decimals

    def _load_function_match(self, cursor: sqlite3.Cursor) -> None:
        """
        Load matched functions stored in a DB file

        :param cursor: sqlite3 cursor to the DB
        :return: None
        """

        i2u = lambda x: ctypes.c_ulonglong(x).value
        fun_query = "SELECT id, address1, address2, similarity, confidence, algorithm FROM function"
        for id, addr1, addr2, sim, conf, alg in cursor.execute(fun_query):
            addr1, addr2 = i2u(addr1), i2u(addr2)
            m = FunctionMatch(id, addr1, addr2, sim, conf, FunctionAlgorithm(alg))
            self.primary_functions_match[addr1] = m
            self.secondary_functions_match[addr2] = m

    def _load_basicblock_match(self, cursor: sqlite3.Cursor) -> None:
        """
        Load matched basic blocks stored in a DB file

        :param cursor: sqlite3 cursor to the DB
        :return: None
        """

        mapping = {x.id: x for x in self.function_matches}
        query = "SELECT id, functionid, address1, address2, algorithm FROM basicblock"
        for id, fun_id, bb_addr1, bb_addr2, bb_algo in cursor.execute(query):
            fun_match = mapping[fun_id]
            assert fun_id == mapping[fun_id].id
            bmatch = BasicBlockMatch(id, fun_match, bb_addr1, bb_addr2, BasicBlockAlgorithm(bb_algo))

            # As a basic block address can be in multiple functions create a nested dictionnary
            if bb_addr1 in self.primary_basicblock_match:
                self.primary_basicblock_match[bb_addr1][fun_match.address1] = bmatch
            else:
                self.primary_basicblock_match[bb_addr1] = {fun_match.address1: bmatch}

            if bb_addr2 in self.secondary_basicblock_match:
                self.secondary_basicblock_match[bb_addr2][fun_match.address2] = bmatch
            else:
                self.secondary_basicblock_match[bb_addr2] = {fun_match.address2: bmatch}

    def _load_instruction_match(self, cursor: sqlite3.Cursor) -> None:
        """
        Load matched instructions stored in a DB file

        :param cursor: sqlite3 cursor to the DB
        :return: None
        """

        i2u = lambda x: ctypes.c_ulonglong(x).value
        mapping = {x.id: x for x in self.basicblock_matches}
        query = "SELECT basicblockid, address1, address2 FROM instruction"
        for id, i_addr1, i_addr2 in cursor.execute(query):
            i_addr1, i_addr2 = i2u(i_addr1), i2u(i_addr2)
            fun_match = mapping[id].function_match

            # Set mapping for instructions
            if i_addr1 in self.primary_instruction_match:
                self.primary_instruction_match[i_addr1][fun_match.address1] = i_addr2
            else:
                self.primary_instruction_match[i_addr1] = {fun_match.address1: i_addr2}

            if i_addr2 in self.secondary_instruction_match:
                self.secondary_instruction_match[i_addr2][fun_match.address2] = i_addr1
            else:
                self.secondary_instruction_match[i_addr2] = {fun_match.address2: i_addr1}
