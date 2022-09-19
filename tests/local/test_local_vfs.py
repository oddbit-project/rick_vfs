import pytest

from rick_vfs.local.local import LocalVolume, LocalVfs
from rick_vfs.utils import get_temp_dir
from rick_vfs.vfs import VfsError


@pytest.fixture()
def volume():
    root = get_temp_dir()
    volume = LocalVolume(root)
    yield volume
    volume.remove()


class TestLocalVfs:

    def test_init(self, volume):
        vfs = LocalVfs(volume)
        assert vfs.volume == volume
        assert vfs.root == volume.root

    def test_mkdir(self, volume):
        vfs = LocalVfs(volume)
        folder_name = 'abc/def'
        info = vfs.stat(folder_name)
        assert info is None  # does not exist
        vfs.mkdir(folder_name)
        info = vfs.stat(folder_name)
        assert info is not None  # item exists
        assert info.is_dir is True
        assert info.is_file is False

    def test_rmdir(self, volume):
        vfs = LocalVfs(volume)
        folder_name = 'abc/def'
        info = vfs.stat(folder_name)
        assert info is None  # does not exist
        vfs.mkdir(folder_name)
        info = vfs.stat(folder_name)
        assert info is not None  # item exists

        # attempt to remove non-existing folder, should raise exception
        with pytest.raises(VfsError):
            vfs.rmdir('xyz')

        # attempt to remove non-empty folder, should raise exception
        with pytest.raises(VfsError):
            vfs.rmdir('abc')

        # attempt to remove root, should raise exception
        with pytest.raises(VfsError):
            for path in ['', '.', './', '/']:
                vfs.rmdir(path)

        # attempt to remove leaf dir, base dir should exist
        vfs.rmdir(folder_name)
        assert vfs.stat(folder_name) is None  # leaf dir must not exist
        assert vfs.stat('abc') is not None  # base dir should exist
