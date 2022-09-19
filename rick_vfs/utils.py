import copy
import copyreg
import tempfile
from collections import OrderedDict
from pathlib import Path


def dict_extract(src: dict, key: str, default=None):
    if key in src.keys():
        return src[key]
    return default


def ordered_dict_to_dict(src: OrderedDict) -> dict:
    """
    Converts a nested OrderedDict structure to plain dicts
    Code adapted from: https://stackoverflow.com/questions/56494304/how-can-i-do-to-convert-ordereddict-to-dict

    Returns:
        A copy of the input, in which all OrderedDicts contained
        anywhere in the input (as iterable items or attributes, etc.)
        have been converted to plain dicts.
    """
    if not isinstance(src, OrderedDict):
        return {}

    if len(src.keys()) == 0:
        return {}

    # Temporarily install a custom pickling function
    # (used by deepcopy) to convert OrderedDict to dict.
    orig_pickler = copyreg.dispatch_table.get(OrderedDict, None)
    copyreg.pickle(
        OrderedDict,
        lambda d: (dict, ([*d.items()],))
    )
    try:
        return copy.deepcopy(src)
    finally:
        # Restore the original OrderedDict pickling function (if any)
        del copyreg.dispatch_table[OrderedDict]
        if orig_pickler:
            copyreg.dispatch_table[OrderedDict] = orig_pickler


def get_temp_dir() -> Path:
    """
    Returns a non-existing temporary directory
    :return:
    """
    while True:
        result = Path(tempfile.gettempdir()) / Path(next(tempfile._get_candidate_names()))
        if not result.exists():
            return result
