import os
import tempfile
from pathlib import Path

import pytest

from rick_vfs.local.local import LocalVolume
from rick_vfs.utils import get_temp_dir

resolve_paths = [
    ['../test', '/tmp/test'],
    ['../../test', '/tmp/test'],
    ['../../abc/../test', '/tmp/test'],
    ['../../abc/../test/fixtures', '/tmp/test/fixtures'],
    ['../../abc/../.test/fixtures', '/tmp/.test/fixtures'],
    ['/test/foo', '/tmp/test/foo'],
    ['./test/jkl', '/tmp/test/jkl'],
    ['.test/xyz', '/tmp/.test/xyz'],
    ['abc', '/tmp/abc']
]


def test_init():
    # test with existing temp folder
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        volume = LocalVolume(root)
        assert volume.exists() is True
        assert volume.root_path() == str(root)
        assert volume.resolve_path('a/b/c') == root / Path('a/b/c')

    # test with non-existing temp folder, auto_create=True
    root = get_temp_dir()
    assert root.exists() is False
    volume = LocalVolume(root)
    assert volume.exists() is True
    assert volume.root_path() == str(root)
    assert volume.resolve_path('a/b/c') == root / Path('a/b/c')
    volume.remove()  # destroy volume
    assert root.exists() is False

    # test with non-existing temp folder, auto_create=False
    root = get_temp_dir()
    assert root.exists() is False
    volume = LocalVolume(root, auto_create=False)
    assert volume.exists() is False  # volume should not exist
    assert volume.root_path() == str(root)
    assert volume.resolve_path('a/b/c') == root / Path('a/b/c')


def test_remove_purge():
    root = get_temp_dir()
    assert root.exists() is False
    volume = LocalVolume(root)
    assert volume.exists() is True

    # manually add stuff to the volume
    os.makedirs(root / Path('a/b/c'))

    # destroy volume
    volume.purge()
    assert volume.exists() is False
    assert root.exists() is False


def test_create():
    root = get_temp_dir()
    assert root.exists() is False
    volume = LocalVolume(root, auto_create=False)
    # create volume
    volume.create()
    assert volume.exists() is True
    assert volume.root_path() == str(root)
    volume.purge()


@pytest.mark.parametrize('prel, pabs', resolve_paths)
def test_resolve_path(prel, pabs):
    obj = LocalVolume('/tmp')
    assert pabs == str(obj.resolve_path(prel))
