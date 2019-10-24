import os
from pathlib import Path

BINDIFF_PATH_ENV = "BINDIFF_PATH"
BIN_NAMES = ['bindiff', 'differ']
BINDIFF_BINARY = None

def __check_bin_names(path: Path) -> bool:
    global BINDIFF_BINARY
    for name in BIN_NAMES:
        bin_path = path / name
        if bin_path.exists():
            BINDIFF_BINARY = bin_path.resolve().absolute()
            return True

    return False


def __check_environ() -> bool:
    if BINDIFF_PATH_ENV in os.environ:
        return __check_bin_names(Path(os.environ[BINDIFF_PATH_ENV]))

    return False


def __check_default_path() -> bool:
    return __check_bin_names(Path("/opt/zynamics/BinDiff/bin"))


def __check_path() -> bool:
    if "PATH" in os.environ:
        for p in os.environ["PATH"].split(":"):
            if __check_bin_names(Path(p)):
                return True

    return False


if not __check_environ():
    if not __check_default_path():
        if not __check_path():
            raise ImportError("BinDiff differ executable not found, should be in $PATH or %s env variable" %
                              BINDIFF_PATH_ENV)

from bindiff.bindiff import BinDiff
