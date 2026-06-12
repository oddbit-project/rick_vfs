import tempfile
import uuid
from pathlib import Path


def dict_extract(src: dict, key: str, default=None):
    if key in src.keys():
        return src[key]
    return default


def get_temp_dir() -> Path:
    """
    Returns a non-existing temporary directory
    :return:
    """
    while True:
        result = Path(tempfile.gettempdir()) / uuid.uuid4().hex
        if not result.exists():
            return result
