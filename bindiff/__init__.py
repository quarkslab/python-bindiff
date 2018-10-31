import os
from pathlib import Path

BINDIFF_PATH_ENV = "BINDIFF_PATH"
BIN_NAME = "differ"
BINDIFF_BINARY = None


def __check_environ() -> bool:
    global BINDIFF_BINARY
    if BINDIFF_PATH_ENV in os.environ:
        if (Path(os.environ[BINDIFF_PATH_ENV]) / BIN_NAME).exists():
            BINDIFF_BINARY = (Path(os.environ[BINDIFF_PATH_ENV]) / BIN_NAME).resolve()
            return True
    return False


def __check_default_path() -> bool:
    global BINDIFF_BINARY
    p = Path("/opt/zynamics/BinDiff/bin") / BIN_NAME
    if p.exists():
        BINDIFF_BINARY = p.resolve()
        return True
    else:
        return False


def __check_path() -> bool:
    global BINDIFF_BINARY
    if "PATH" in os.environ:
        for p in os.environ["PATH"].split(":"):
            if (Path(p) / BIN_NAME).exists():
                BINDIFF_BINARY = (Path(p) / BIN_NAME).resolve()
                return True
    return False


if not __check_environ():
    if not __check_default_path():
        if not __check_path():
            raise ImportError("BinDiff differ executable not found, should be in $PATH or %s env variable" %
                              BINDIFF_PATH_ENV)

from bindiff.bindiff import BinDiff