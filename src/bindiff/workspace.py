from pathlib import Path
import sqlite3
from datetime import datetime
from dataclasses import dataclass
from typing import Union
import ctypes


@dataclass
class Diffs:
    """
    A workspace diff entry
    """
    path: Path            #: Path to diff file
    isfunctiondiff: bool  #: Whether the diff is solely a function diff
    


class BindiffWorkspace(object):
    """
    Bindiff workspace database file. The class enables crafting a ready
    to open bindiff workspace.
    """

    def __init__(self, file: Union[Path, str], permission: str = "ro"):
        """
        :param file: path to Bindiff database
        :param permission: database permissions (default: ro)
        """
        assert permission in ["ro", "rw"]

        self._file = Path(file).absolute()

        if self._file.exists():
            # Open database
            self.db = sqlite3.connect(f"file:{str(self._file)}?mode={permission}", uri=True)
        else:
            # Create database
            self.db = sqlite3.connect(str(self._file))
            self.init_database()


    @property
    def diffs(self) -> list[Diffs]:
        """
        Returns the list of matched functions
        """
        cursor = self.db.cursor()
        cursor.execute("SELECT matchesDbPath, isfunctiondiff FROM diffs")
        rows = cursor.fetchall()
        return [Diffs(self._file.parent / row[0], bool(row[1])) for row in rows]


    def add_diff(self, diff_path: Union[Path, str], is_function_diff: bool) -> None:
        """
        Add a diff entry to the workspace

        :param diff_path: path to diff file
        :param is_function_diff: whether the diff is solely a function diff
        :return: None
        """
        cursor = self.db.cursor()
        diff_path = Path(diff_path)

        cursor.execute(
            """
            INSERT INTO diffs (matchesDbPath, isfunctiondiff) VALUES (:path, :isfunctiondiff)
            """,
            {
                "path": str(diff_path.relative_to(self._file.parent)),
                "isfunctiondiff": int(is_function_diff)
            },
        )


    def init_database(self) -> None:
        """
        Initialize the database by creating all the tables
        """
        conn = self.db.cursor()
        # fmt: off
        conn.execute("""
                     CREATE TABLE bd_basicblockComments (pe_hash VARCHAR(40) NOT NULL, functionAddr BIGINT NOT NULL,
                     basicblockAddr BIGINT NOT NULL, comment long VARCHAR NOT NULL, primary key (pe_hash, functionAddr, basicblockAddr))
                     """)
        conn.execute("""
                     CREATE TABLE bd_instructionComments(pe_hash VARCHAR(40) NOT NULL, functionAddr BIGINT NOT NULL,
                     instructionAddr BIGINT NOT NULL, placement SMALLINT NOT NULL, comment long VARCHAR NOT NULL,
                     PRIMARY KEY (pe_hash, functionAddr, instructionAddr, placement))""")
        conn.execute("""CREATE TABLE diffs (matchesDbPath VARCHAR NOT NULL, isfunctiondiff NUMERIC NOT NULL DEFAULT 0)""")
        conn.execute("""CREATE TABLE metadata (version INT NOT NULL)""")
        self.db.commit()


    @staticmethod
    def create(filename: str|Path) -> 'BindiffWorkspace':
        """
        Create a new BindiffWorkspace database file.

        :param filename: database file path
        """
        # Remove workspace if it already exists
        if Path(filename).exists():
            Path(filename).unlink()

        return BindiffWorkspace(filename, permission="rw")


    def commit(self) -> None:
        """
        Commit all pending transaction in the database.
        """
        self.db.commit()

    def close(self) -> None:
        """
        Close the database connection.
        """
        self.db.commit()
        self.db.close()
