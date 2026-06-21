#!/usr/bin/env python3
# coding: utf-8

import logging
import os
import traceback
from pathlib import Path
import queue
from typing import Generator
import magic
import click
import sys

from multiprocessing import Pool, Queue, Manager

from bindiff import BinDiff, BindiffWorkspace
from binexport import ProgramBinExport, DisassemblerBackend, check_disassembler_availability


BINARY_FORMAT = {
    "application/x-dosexec",
    "application/x-sharedlib",
    "application/x-mach-binary",
    "application/x-executable",
    "application/x-object",
    "application/x-pie-executable",
}

EXTENSIONS_WHITELIST = {"application/octet-stream": [".dex"]}


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"], max_content_width=300)

class Bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def iter_directories(p1: Path, p2: Path) -> Generator[tuple[Path, Path], None, None]:
    """
    Iterate any two directories to compare files that have the exact same
    name. If any two files already have a BinExport file. It will be used
    instead of the binary.
    """
    to_ignore = set()
    for file1 in p1.iterdir():
        # Skip files marked to be ignored (as already processed)
        if file1 in to_ignore:
            pass

        if file1.is_file():  # If its a file
            mime_type = magic.from_file(str(file1), mime=True)
            # If it has the right mimetype
            if mime_type in BINARY_FORMAT or file1.suffix in EXTENSIONS_WHITELIST.get(mime_type, []):
                file2 = p2/ file1.name
                # If a file exists in the second directory with the same name
                if file2.exists():
                    # Check if there is a BinExport version
                    file1_binexport = file1.with_suffix(file1.suffix + ".BinExport")
                    if file1_binexport.exists():
                        to_ignore.add(file1_binexport)
                        file1 = file1_binexport  # Use the BinExport already present

                    file2_binexport = file2.with_suffix(file2.suffix + ".BinExport")
                    if file2_binexport.exists():
                        file2 = file2_binexport

                    yield file1, file2
        elif file1.is_dir():
            pass  # Ignore directories (not recursive)
        else:
            pass  # Ignore symlinks & co


def diffing_job(ingress, egress, output: Path|None, single: bool, backend: DisassemblerBackend, timeout: int | None) -> None:
    while True:
        try:
            primary, secondary = ingress.get(timeout=0.5)

            # Compute destination diff file
            if output is None:
                diff_output = f"{primary.stem}_vs_{secondary.stem}.BinDiff"
            elif not single and output is not None:
                # In Batch mode we need to create an additional directory to store the BinDiff into
                # the reason is that BinDiff uses the parent directory to represent a diff in the UI.
                diff_dir = output / primary.stem
                diff_dir.mkdir(exist_ok=True)
                diff_output = diff_dir / f"{primary.stem}_vs_{secondary.stem}.BinDiff"
            elif single and output is not None:
                diff_output = output

                # Check that the output name is not too long
                if len(str(diff_output)) > 255:
                    logging.error("Output file name is too long (%s).", output)
                    exit(1)
            else:
                assert False

            # Export primary if needed
            if primary.suffix != ".BinExport":
                logging.info(f"export primary: {primary}.BinExport")
                primary = ProgramBinExport.generate(primary.as_posix(), backend=backend, timeout=timeout)
            
            # Export secondary if needed
            if secondary.suffix != ".BinExport":  # Export primary
                logging.info(f"export secondary: {secondary}.BinExport")
                secondary = ProgramBinExport.generate(secondary.as_posix(), backend=backend, timeout=timeout)
            
            # Diffing both binexports
            logging.info("start diffing")
            if BinDiff.raw_diffing(primary, secondary, diff_output):
                logging.info(f"diffing file written to: {diff_output}")
                res = True
            else:
                logging.error(f"Diffing failed")
                res = False

            egress.put((diff_output, res))
        except queue.Empty:
            pass
        except KeyboardInterrupt:
            break
        except Exception as e:
            # Might not be printed as triggered withing a fork
            logging.error(traceback.format_exception(e))
            egress.put((None, e))



@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "-d",
    "--disassembler",
    type=click.Choice([x.name.lower() for x in DisassemblerBackend], case_sensitive=False),
    default="ida",
    help="Disassembler to use",
)
@click.option(
    "--disass-path",
    type=str,
    default="",
    help="Path of the disassembler (dir or binary for IDA, dir for Ghidra)" \
    "(if not provided search $PATH or environment variable IDA_PATH, GHIDRA_PATH)",
)
@click.option("-t", "--threads", type=int, default=1, help="Thread number to use")
@click.option(
    "--timeout",
    type=int,
    default=None,
    help="Per-file export timeout in seconds (if not set, no timeout is enforced)",
)
@click.option(
    "-b",
    "--bindiff-path",
    type=click.Path(exists=True),
    default=None,
    help="BinDiff differ directory",
)
@click.option("--stop-on-error", is_flag=True, default=False, help="Stop on error")
@click.option("-o", "--output", type=click.Path(path_type=Path),
              default=None, help="Output BinDiff file, or directory for batch")
@click.option("--override", is_flag=True, default=False,
              help="Override existing output files (includes .BinExport files)")
@click.option("-bw", "--bindiff-workspace", type=click.Path(path_type=Path), default=None,
              help="Create a BinDiff Workspace database")
@click.argument("primary", type=click.Path(exists=True, path_type=Path),
                metavar="<primary file|dir>")
@click.argument("secondary", type=click.Path(exists=True, path_type=Path),
                metavar="<secondary file|dir>")
def main(disassembler: str,
         disass_path: str,
         threads: int,
         timeout: int|None,
         bindiff_path: str,
         stop_on_error: bool,
         output: Path|None,
         override: bool,
         primary: Path,
         secondary: Path,
         bindiff_workspace: Path | None) -> None:
    """
    bindiffer is a very simple utility to diff two binary files using BinDiff
    in command line. The two input files can be either binary files (in which
    case IDA is used) or directly .BinExport file (solely BinDiff is used).

    :param disassembler: Disassembler to use for BinExport generation
    :param disass_path: Path to the disassembler if it has to be provided
    :param threads: Number of parrallel jobs for bulk directory diffing
    :param timeout: Timeout per export or diffing task
    :param bindiff_path: Path to the BinDiff folder
    :param stop_on_error: whether stopping the whole diffing process if one fails
    :param output: Path for the output diffing file
    :param override: Whether to override existing output files
    :param primary: Path to the primary file or directory
    :param secondary: Path to the secondary file or directory
    :param bindiff_workspace: Path to the BinDiff workspace database to create
    """

    logging.basicConfig(format="[%(levelname)s] %(message)s", level=logging.INFO)

    # Get enum from string
    engine = DisassemblerBackend[disassembler.upper()]

    # Check disassembler availability
    if not check_disassembler_availability(engine, disass_path):
        logging.error(f"Error trying to find disassembler {engine.name.lower()}")
        return

    if bindiff_path:
        os.environ["BINDIFF_PATH"] = Path(bindiff_path).resolve().as_posix()

    if not BinDiff.is_installation_ok():
        logging.error(
            "can't find bindiff executable (make sure its available in $PATH or via --bindiff-path"
        )
        sys.exit(1)


    manager = Manager()
    ingress = manager.Queue()
    egress = manager.Queue()
    pool = Pool(threads)


    # Single diff mode
    if primary.is_file() and secondary.is_file():
        ingress.put((primary, secondary))
        total = 1
        single = True

    # Batch diff mode
    elif primary.is_dir() and secondary.is_dir():
        # Pre-fill ingress queue
        total = 0
        single = False

        # Make sure output is okay
        if output is not None:
            if output.exists():
                if not output.is_dir():
                    logging.error("For batch diffing output should be a directory")
                    sys.exit(1)
            else:
                output.mkdir()

        # Iter primary directory to identify files to diff
        for file1, file2 in iter_directories(primary, secondary):
            ingress.put((file1, file2))
            total += 1
    else:
        logging.error("primary and secondary should be of the same type (either file, or directory)")
        sys.exit(1)

    # Launch all workers
    for _ in range(threads):
        pool.apply_async(diffing_job, (ingress, egress, output, single, engine, timeout))

    logging.info(f"Start diffing {total} binar{'ies' if total > 1 else 'y'} with {engine.name} backend")


    diffs_files = []
    i = 0
    while True:
        item = egress.get()
        i += 1
        path, res = item

        # Check if the result is an exception
        if isinstance(res, Exception):
            logging.error(f"Error while processing {path}: {res}")
            if stop_on_error:
                logging.error(traceback.format_exception(res))
                pool.terminate()
                break
            else:
                res = False # set to false and just print KO
        
        # Print the result
        if res:
            pp_res = Bcolors.OKGREEN + "OK" + Bcolors.ENDC
            diffs_files.append(path)
        else:
            pp_res = Bcolors.FAIL + "KO" + Bcolors.ENDC
        
        # print stats
        logging.info(f"[{i}/{total}] {str(path)} [{pp_res}]")
        if i == total:
            break

    pool.terminate()

    
    # Create the BinDiff workspace
    if bindiff_workspace:
        ws_file = Path(bindiff_workspace)

        # Force .BinDiffWorkspace extension otherwise it can be opened
        if ws_file.suffix != ".BinDiffWorkspace":
            ws_file = Path(str(ws_file)+".BinDiffWorkspace")

        # Create workspace and add the diffs
        workspace = BindiffWorkspace(ws_file, permission="rw")

        for diff_file in diffs_files:
            workspace.add_diff(Path(diff_file).absolute(), is_function_diff=False)
        
        workspace.close()
        logging.info(f"Bindiff workspace written at: {bindiff_workspace}")


if __name__ == "__main__":
    main()
