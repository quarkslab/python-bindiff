#!/usr/bin/env python3
# coding: utf-8

import logging
import os
from pathlib import Path
import magic
import click
import sys

from bindiff import BinDiff
from binexport import ProgramBinExport

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


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "-i",
    "--ida-path",
    type=click.Path(exists=True),
    default=None,
    help="IDA Pro installation directory",
)
@click.option(
    "-b",
    "--bindiff-path",
    type=click.Path(exists=True),
    default=None,
    help="BinDiff differ directory",
)
@click.option("-o", "--output", type=click.Path(), default=None, help="Output file matching")
@click.argument("primary", type=click.Path(exists=True), metavar="<primary file>")
@click.argument("secondary", type=click.Path(exists=True), metavar="<secondary file>")
def main(ida_path: str, bindiff_path: str, output: str, primary: str, secondary: str) -> None:
    """
    bindiffer is a very simple utility to diff two binary files using BinDiff
    in command line. The two input files can be either binary files (in which
    case IDA is used) or directly .BinExport file (solely BinDiff is used).

    :param ida_path: Path to the IDA pro folder
    :param bindiff_path: Path to the BinDiff folder
    :param output: Path for the output diffing file
    :param primary: Path to the primary file
    :param secondary: Path to the secondary file
    """

    logging.basicConfig(format="[%(levelname)s] %(message)s", level=logging.INFO)

    if ida_path:
        os.environ["IDA_PATH"] = Path(ida_path).resolve().as_posix()

    if bindiff_path:
        os.environ["BINDIFF_PATH"] = Path(bindiff_path).resolve().as_posix()

    if not BinDiff.is_installation_ok():
        logging.error(
            "can't find bindiff executable (make sure its available in $PATH or via --bindiff-path"
        )
        sys.exit(1)

    if output is None:
        output = "{}_vs_{}.BinDiff".format(Path(primary).stem, Path(secondary).stem)

    # Check that the output name is not too long
    if len(output) > 255:
        logging.error("Output file name is too long (%s).", output)
        exit(1)

    primary = Path(primary)
    secondary = Path(secondary)

    if not (primary.suffix == ".BinExport" and secondary.suffix == ".BinExport"):
        for file in [primary, secondary]:
            mime_type = magic.from_file(file, mime=True)
            if mime_type not in BINARY_FORMAT and Path(file).suffix not in EXTENSIONS_WHITELIST.get(
                mime_type, []
            ):
                logging.error(
                    f"file {file} mimetype ({mime_type}) not supported (not an executable file)"
                )
                exit(1)

        # Export each binary separately (and then diff to be able to print it)
        logging.info(f"export primary: {primary}.BinExport")
        ProgramBinExport.from_binary_file(primary, open_export=False, override=True)
        primary = Path(str(primary) + ".BinExport")

        logging.info(f"export secondary: {secondary}.BinExport")
        ProgramBinExport.from_binary_file(secondary, open_export=False, override=True)
        secondary = Path(str(secondary) + ".BinExport")

    logging.info("start diffing")
    if BinDiff.raw_diffing(primary, secondary, output):
        logging.info(f"diffing file written to: {output}")
        sys.exit(0)
    else:
        logging.error(f"Diffing failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
