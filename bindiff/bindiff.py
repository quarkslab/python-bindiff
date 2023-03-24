# from __future__ import annotations  #put it back when python 3.7 will be widely adopted
from __future__ import absolute_import
import logging
import shutil
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Union, Optional

from binexport import ProgramBinExport

from bindiff.types import ProgramBinDiff, FunctionBinDiff, BasicBlockBinDiff, InstructionBinDiff, BindiffNotFound
from bindiff import BindiffFile


BINDIFF_BINARY = None
BINDIFF_PATH_ENV = "BINDIFF_PATH"
BIN_NAMES = ['bindiff', 'bindiff.exe', 'differ']


def _check_bin_names(path: Path) -> bool:
    """
    Check if one of the BinDiff binary exists

    :param path: Path to the binary
    :return: bool
    """

    global BINDIFF_BINARY
    for name in BIN_NAMES:
        bin_path = path / name
        if bin_path.exists():
            BINDIFF_BINARY = bin_path.resolve().absolute()
            return True
    return False


def _check_environ() -> bool:
    """
    Check if BinDiff is already installed

    :return: bool
    """

    if BINDIFF_PATH_ENV in os.environ:
        return _check_bin_names(Path(os.environ[BINDIFF_PATH_ENV]))
    return False


def _check_default_path() -> bool:
    """
    Check if BinDiff is installed at its default location
    
    :return: bool
    """

    return _check_bin_names(Path("/opt/zynamics/BinDiff/bin"))


def _check_path() -> bool:
    """
    Check if the environment variable PATH contains BinDiff binaries

    :return: bool
    """

    if "PATH" in os.environ:
        for p in os.environ["PATH"].split(os.pathsep):
            if _check_bin_names(Path(p)):
                return True
    return False


class BinDiff(BindiffFile):
    """
    BinDiff class. Parse the diffing result of Bindiff and apply it to the two
    ProgramBinExport given. All the diff result is embedded in the two programs
    object so after loading the class can be dropped if needed.
    """

    def __init__(self, primary: Union[ProgramBinExport, str], secondary: Union[ProgramBinExport, str], diff_file: str):
        """
        BinDiff construct. Takes the two program and the diffing result file.
        Load the two programs if not given as ProgramBinExport object.
        .. warning:: the two programs given are mutated into ProgramBinDiff classes

        :param primary: first program diffed
        :param secondary: second program diffed
        :param diff_file: diffing file as generated by bindiff (differ more specifically)
        """

        super(BinDiff, self).__init__(diff_file)

        self.primary = ProgramBinExport(primary) if isinstance(primary, str) else primary
        self.secondary = ProgramBinExport(secondary) if isinstance(secondary, str) else secondary
        self._convert_program_classes(self.primary)
        self._convert_program_classes(self.secondary)

        self._map_diff_on_programs()

    @staticmethod
    def _convert_program_classes(p: ProgramBinExport) -> None:
        """
        Internal method to mutate a ProgramBinExport into ProgramBinDiff.

        :param p: program to mutate
        :return: None (perform all the side effect on the program)
        """

        p.__class__ = ProgramBinDiff
        for f in p.values():
            f.__class__ = FunctionBinDiff
            for bb in f.values():
                bb.__class__ = BasicBlockBinDiff
                for i in bb.values():
                    i.__class__ = InstructionBinDiff

    def _map_diff_on_programs(self) -> None:
        """
        From a diffing result, maps functions, basic blocks and instructions of primary and secondary

        :return: None
        """

        # Map similarity and confidence on both programs
        self.primary.similarity, self.secondary.similarity = self.similarity, self.similarity
        self.primary.confidence, self.secondary.confidence = self.confidence, self.confidence

        for match in self.function_matches:
            f1 = self.primary[match.address1]
            f2 = self.secondary[match.address2]
            f1.similarity = f2.similarity = match.similarity
            f1.confidence = f2.confidence = match.confidence
            f1.algorithm = f2.algorithm = match.algorithm
            f1.match, f2.match = f2, f1

            # print("Function:", f1)
            for bb_f1 in f1.values():

                # The basicblock is matched by a function
                if bb_f1.addr in self.primary_basicblock_match:
                    # The basicblock is matched within our function
                    if f1.addr in self.primary_basicblock_match[bb_f1.addr]:
                        # retrieve the match of the basic block
                        bb_match = self.primary_basicblock_match[bb_f1.addr][f1.addr]
                        assert match == bb_match.function_match

                        # retrieve basic block in secondary
                        bb_f2 = f2[bb_match.address2]

                        # Map info
                        bb_f1.match, bb_f2.match = bb_f2, bb_f1
                        bb_f1.algorithhm = bb_f2.algorithm = bb_match.algorithm

                        # Iterate instructions to map them
                        for ins_f1 in bb_f1.values():
                            # Instruction is matched
                            if ins_f1.addr in self.primary_instruction_match:
                                # Within the context of the current function
                                if f1.addr in self.primary_instruction_match[ins_f1.addr]:
                                    ins_f2_addr = self.primary_instruction_match[ins_f1.addr][f1.addr]
                                    ins_f2 = bb_f2[ins_f2_addr]  # retrieve instruction in secondary basic block
                                    ins_f1.match, ins_f2.match = ins_f2, ins_f1

    @staticmethod
    def raw_diffing(p1_path: Union[Path, str], p2_path: Union[Path, str], out_diff: str) -> bool:
        """
        Static method to diff two binexport files against each other and storing
        the diffing result in the given file

        :param p1_path: primary file path
        :param p2_path: secondary file path
        :param out_diff: diffing output file
        :return: int (0 if successfull, -x otherwise)
        """

        # Make sure the bindiff binary is okay before doing any diffing
        BinDiff.assert_installation_ok()

        tmp_dir = Path(tempfile.mkdtemp())
        f1 = Path(p1_path)
        f2 = Path(p2_path)

        cmd_line = [BINDIFF_BINARY.as_posix(),
                    f"--primary={p1_path}",
                    f"--secondary={p2_path}",
                    f"--output_dir={tmp_dir.as_posix()}"]

        logging.debug(f"run diffing: {' '.join(cmd_line)}")
        process = subprocess.Popen(cmd_line, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        retcode = process.wait()
        if retcode != 0:
            logging.error(f"differ terminated with error code: {retcode}")
            return False
        # Now look for the generated file
        out_file = tmp_dir / "{}_vs_{}.BinDiff".format(f1.stem, f2.stem)
        if out_file.exists():
            shutil.move(out_file, out_diff)
        else:  # try iterating the directory to find the .BinExport file
            candidates = list(tmp_dir.iterdir())
            if len(candidates) > 1:
                logging.warning("the output directory not meant to contain multiple files")
            found = False
            for file in candidates:
                if file.suffix == ".BinExport":
                    shutil.move(file, out_diff)
                    found = True
                    break
            if not found:
                logging.error("diff file .BinExport not found")
                return False
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return True

    @staticmethod
    def from_binary_files(p1_path: str, p2_path: str, diff_out: str) -> Optional['BinDiff']:
        """
        Diff two executable files. Thus it export .BinExport files from IDA
        and then diff the two resulting files in BinDiff.

        :param p1_path: primary binary file to diff
        :param p2_path: secondary binary file to diff
        :param diff_out: output file for the diff
        :return: BinDiff object representing the diff
        """

        p1 = ProgramBinExport.from_binary_file(p1_path)
        p2 = ProgramBinExport.from_binary_file(p2_path)
        p1_binexport = Path(f"{p1_path}.BinExport")
        p2_binexport = Path(f"{p2_path}.BinExport")
        if p1 and p2:
            retcode = BinDiff.raw_diffing(p1_binexport, p2_binexport, diff_out)
            return BinDiff(p1, p2, diff_out) if retcode else None
        else:
            logging.error("p1 or p2 could not have been 'binexported'")
            return None

    @staticmethod
    def from_binexport_files(p1_binexport: str, p2_binexport: str, diff_out: str) -> Optional['BinDiff']:
        """
        Diff two binexport files. Diff the two binexport files with bindiff
        and then load a BinDiff instance.

        :param p1_binexport: primary binexport file to diff
        :param p2_binexport: secondary binexport file to diff
        :param diff_out: output file for the diff
        :return: BinDiff object representing the diff
        """

        retcode = BinDiff.raw_diffing(p1_binexport, p2_binexport, diff_out)
        return BinDiff(p1_binexport, p2_binexport, diff_out) if retcode else None

    @staticmethod
    def _configure_bindiff_path() -> None:
        """
        Check BinDiff access paths

        :return: None
        """

        if not _check_environ():
            if not _check_default_path():
                if not _check_path():
                    logging.warning(f"Can't find a valid bindiff executable. (should be available in PATH or"
                                    f"as ${BINDIFF_PATH_ENV} env variable")

    @staticmethod
    def assert_installation_ok() -> None:
        """
        Assert BinDiff is installed

        :return: None
        """

        BinDiff._configure_bindiff_path()
        if BINDIFF_BINARY is None:
            raise BindiffNotFound()

    @staticmethod
    def is_installation_ok() -> bool:
        """
        Check that bindiff is properly installed and can be found
        on the system.

        :return: true if the bindiff binary can be found.
        """

        try:
            BinDiff.assert_installation_ok()
            return True
        except BindiffNotFound:
            return False
