from pathlib import Path
import sqlite3
import hashlib
from datetime import datetime
from dataclasses import dataclass
from typing import Union
import ctypes

from bindiff.types import FunctionAlgorithm, BasicBlockAlgorithm


@dataclass
class File:
    """
    File diffed in database.
    """
    id: int             #: Unique ID of the file in database
    filename: str       #: file path
    exefilename: str    #: file name
    hash: str           #: SHA256 hash of the file
    functions: int      #: total number of functions
    libfunctions: int   #: total number of functions identified as library
    calls: int          #: number of calls
    basicblocks: int    #: number of basic blocks
    libbasicblocks: int #: number of basic blocks belonging to library functions
    edges: int          #: number of edges in callgraph
    libedges: int       #: number of edges in callgraph addressing a library
    instructions: int   #: number of instructions
    libinstructions: int  #: number of instructions in library functions


@dataclass
class FunctionMatch:
    """
    A match between two functions in database.
    """
    id: int            #: unique ID of function match in database
    address1: int      #: function address in primary
    address2: int      #: function address in secondary
    similarity: float  #: similarity score (0..1)
    confidence: float  #: confidence of the match (0..1)
    algorithm: FunctionAlgorithm  #: algorithm used for the match


@dataclass
class BasicBlockMatch:
    """
    A match between two basic blocks
    """
    id: int  #: ID of the match in database
    function_match: FunctionMatch  #: FunctionMatch associated with this match
    address1: int  #: basic block address in primary
    address2: int  #: basic block address in secondary
    algorithm: BasicBlockAlgorithm  #: algorithm used to match the basic blocks


class BindiffFile(object):
    """
    Bindiff database file.
    The class seemlessly parse the database and allowing retrieving
    and manipulating the results.

    It also provides some methods to create a database and to add entries
    in the database.
    """
    def __init__(self, file: Union[Path, str], permission: str = "ro"):
        """
        :param file: path to Bindiff database
        :param permission: permission to use for opening database (default: ro)
        """
        self._file = file
        
        # Open database
        self.db = sqlite3.connect(f"file:{str(file)}?mode={permission}", uri=True)
        
        # Global variables
        self.similarity: float = None  #: Overall similarity
        self.confidence: float = None  #: Overall diffing confidence
        self.version: str = None       #: version of the differ used for diffing
        self.created: datetime = None  #: Database creation date
        self.modified: datetime = None #: Database last modification date
        self._load_metadata(self.db.cursor())

        # Files
        self.primary: File = None    #: Primary file
        self.secondary: File = None  #: Secondary file
        self._load_file(self.db.cursor())

        # Function matches
        self.primary_functions_match: dict[int, FunctionMatch] = {}    #: FunctionMatch indexed by addresses in primary
        self.secondary_functions_match: dict[int, FunctionMatch] = {}  #: FunctionMatch indexed by addresses in secondary
        self._load_function_match(self.db.cursor())

        # Basicblock matches
        self.primary_basicblock_match: dict[int, dict[int, BasicBlockMatch]] = {}    #: Basic block match from primary
        self.secondary_basicblock_match: dict[int, dict[int, BasicBlockMatch]] = {}  #: Basic block match from secondary
        self._load_basicblock_match(self.db.cursor())

        # Instruction matches
        self.primary_instruction_match = {}
        self.secondary_instruction_match = {}
        self._load_instruction_match(self.db.cursor())

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
    def function_matches(self) -> list[FunctionMatch]:
        """
        Returns the list of matched functions
        """
        return list(self.primary_functions_match.values())

    @property
    def basicblock_matches(self) -> list[BasicBlockMatch]:
        """
        Returns the list of matched basic blocks in primary (and secondary)
        """
        return [x for bb_matches in self.primary_basicblock_match.values() for x in bb_matches.values()]

    def _load_file(self, cursor: sqlite3.Cursor) -> None:
        """
        Load diffing file stored in a DB file

        :param cursor: sqlite3 cursor to the DB
        """
        query = "SELECT * FROM file"
        self.primary = File(*cursor.execute(query).fetchone())
        self.secondary = File(*cursor.execute(query).fetchone())

    def _load_metadata(self, cursor: sqlite3.Cursor) -> None:
        """
        Load diffing metadata as stored in the DB file

        :param cursor: sqlite3 cursor to the DB
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

    @staticmethod
    def init_database(db: sqlite3.Connection) -> None:
        """
        Initialize the database by creating all the tables
        """
        conn = db.cursor()
        conn.execute("""
                     CREATE TABLE file (id INTEGER PRIMARY KEY, filename TEXT, exefilename TEXT, hash CHARACTER(40),
                     functions INT, libfunctions INT, calls INT, basicblocks INT, libbasicblocks INT, edges INT,
                     libedges INT, instructions INT, libinstructions INT)""")
        conn.execute("""
                     CREATE TABLE metadata (version TEXT, file1 INTEGER, file2 INTEGER, description TEXT, created DATE,
                     modified DATE, similarity DOUBLE PRECISION, confidence DOUBLE PRECISION,
                     FOREIGN KEY(file1) REFERENCES file(id), FOREIGN KEY(file2) REFERENCES file(id))""")
        conn.execute("""CREATE TABLE functionalgorithm (id SMALLINT PRIMARY KEY, name TEXT)""")
        conn.execute("""
                     CREATE TABLE function (id INTEGER PRIMARY KEY, address1 BIGINT, name1 TEXT, address2 BIGINT,
                     name2 TEXT, similarity DOUBLE PRECISION, confidence DOUBLE PRECISION, flags INTEGER,
                     algorithm SMALLINT, evaluate BOOLEAN, commentsported BOOLEAN, basicblocks INTEGER,
                     edges INTEGER, instructions INTEGER, UNIQUE(address1, address2),
                     FOREIGN KEY(algorithm) REFERENCES functionalgorithm(id))""")
        conn.execute("""CREATE TABLE basicblockalgorithm (id INTEGER PRIMARY KEY, name TEXT)""")
        conn.execute("""
                     CREATE TABLE basicblock (id INTEGER, functionid INT, address1 BIGINT, address2 BIGINT,
                     algorithm SMALLINT, evaluate BOOLEAN, PRIMARY KEY(id), FOREIGN KEY(functionid) REFERENCES function(id),
                     FOREIGN KEY(algorithm) REFERENCES basicblockalgorithm(id))""")
        conn.execute("""
                     CREATE TABLE instruction (basicblockid INT, address1 BIGINT, address2 BIGINT,
                     FOREIGN KEY(basicblockid) REFERENCES basicblock(id))""")
        db.commit()

        conn.execute("""INSERT INTO basicblockalgorithm(name) VALUES ("basicBlock: edges prime product")""")
        db.commit()

    @staticmethod
    def create(filename: str, primary: str, secondary: str, version: str, desc: str, similarity: float, confidence: float) -> 'BindiffFile':
        """
        Create a new Bindiff database object in the file given in `filename`.
        It only takes two binaries.

        :param filename: database file path
        :param primary: path to primary binary
        :param secondary: path to secondary binary
        :param version: version of the differ used
        :param desc: description of the database
        :param similarity: similarity score between to two binaries
        :param confidence: confidence of results
        :return: instance of BindiffFile (ready to be filled)
        """
        open(filename, "w").close()
        db = sqlite3.connect(filename)
        BindiffFile.init_database(db)

        conn = db.cursor()

        # Save primary
        file1 = Path(primary)
        hash1 = hashlib.sha256(file1.read_bytes()).hexdigest() if file1.exists() else ""
        conn.execute("""INSERT INTO file (filename, exefilename, hash) VALUES (:filename, :name, :hash)""",
                     {"filename": str(file1), "name": file1.name, "hash": hash1})

        
        # Save secondary
        file2 = Path(secondary)
        hash2 = hashlib.sha256(file2.read_bytes()).hexdigest() if file2.exists() else ""
        conn.execute("""INSERT INTO file (filename, exefilename, hash) VALUES (:filename, :name, :hash)""",
                     {"filename": str(file2), "name": file2.name, "hash": hash2})
                
        conn.execute(
            """
            INSERT INTO metadata (version, file1, file2, description, created, modified, similarity, confidence)
            VALUES (:version, 1, 2, :desc, :created, :modified, :similarity, :confidence)
            """,
            {
                "version": version,
                "desc": desc,
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "modified":datetime.now().strftime("%Y-%m-%d %H:%M:%S"), # modified has to be filled so initialize it to the creation time
                "similarity": similarity,
                "confidence": confidence
            }
        )
        
        db.commit()
        db.close()
        return BindiffFile(filename, permission="rw")


    def add_function_match(self, fun_addr1: int, fun_addr2: int, fun_name1: str, fun_name2: str, similarity: float, confidence: float = 0.0, identical_bbs: int = 0) -> int:
        """
        Add a function match in database.

        :param fun_addr1: primary function address
        :param fun_addr2: secondary function address
        :param fun_name1: primary function name
        :param fun_name2: secondary function name
        :param similarity: similarity score between the two functions
        :param confidence: confidence score between the two functions
        :param identical_bbs: number of identical basic blocks
        :return: id of the row inserted in database.
        """
        cursor = self.db.cursor()
        cursor.execute(
            """
            INSERT INTO function (address1, address2, name1, name2, similarity, confidence, basicblocks)
            VALUES (:address1, :address2, :name1, :name2, :similarity, :confidence, :identical_bbs)
            """,
            {
                "address1": fun_addr1,
                "address2": fun_addr2,
                "name1": fun_name1,
                "name2": fun_name2,
                "similarity": similarity,
                "confidence": confidence,
                "identical_bbs": identical_bbs
            }
        )
        return cursor.lastrowid

    def add_basic_block_match(self, fun_addr1: int, fun_addr2: int, bb_addr1: int, bb_addr2: int) -> int:
        """
        Add a basic block match in database.

        :param fun_addr1: function address of basic block in primary
        :param fun_addr2: function address of basic block in secondary
        :param bb_addr1: basic block address in primary
        :param bb_addr2: basic block address in secondary
        :return: id of the row inserted in database.
        """
        cursor = self.db.cursor()

        cursor.execute(
            """
            INSERT INTO basicblock (functionid, address1, address2, algorithm)
            VALUES ((SELECT id FROM function WHERE address1=:function_address1 AND address2=:function_address2), :address1, :address2, :algorithm)
            """,
            {
                "function_address1": fun_addr1,
                "function_address2": fun_addr2,
                "address1": bb_addr1,
                "address2": bb_addr2,
                "algorithm": "1",
            }
        )
        return cursor.lastrowid

    def add_instruction_match(self, entry: int, inst_addr1: int, inst_addr2: int) -> None:
        """
        Add an instruction match in database.

        :param entry: basic block match identifier in database
        :param inst_addr1: instruction address in primary
        :param inst_addr2: instruction address in secondary
        """
        cursor = self.db.cursor()

        cursor.execute(
            """
            INSERT INTO instruction (basicblockid, address1, address2) VALUES (:basicblockid, :address1, :address2)
            """,
            {
                "address1": inst_addr1,
                "address2": inst_addr2,
                "basicblockid": entry,
            }
        )

    def update_file_infos(self, entry_id: int, fun_count: int, lib_count: int, bb_count: int, inst_count: int) -> None:
        """
        Update information about a binary in database (function, basic block count ...)

        :param entry_id: entry of the binary in database (row id)
        :param fun_count: number of functions
        :param lib_count: number of functions flagged as libraries
        :param bb_count: number of basic blocks
        :param inst_count: number of instructions
        """
        cursor = self.db.cursor()

        cursor.execute(
            """
            UPDATE file
            SET functions = :functions, libfunctions = :libfunctions, basicblocks = :basicblocks, instructions = :instructions
            WHERE id = :entry_id
            """,
            {
                "entry_id": str(entry_id),
                "functions": fun_count,
                "libfunctions": lib_count,
                "basicblocks": bb_count,
                "instructions": inst_count,
            },
        )
        self.db.commit()
