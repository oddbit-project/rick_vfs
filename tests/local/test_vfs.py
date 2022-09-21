import os
import stat
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from rick_vfs.local.local import LocalVolume, LocalVfs
from rick_vfs.utils import get_temp_dir
from rick_vfs.vfs import VfsError


@pytest.fixture()
def volume():
    root = get_temp_dir()
    volume = LocalVolume(root)
    yield volume
    volume.purge()


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

    def test_rmfile(self, volume):
        vfs = LocalVfs(volume)
        # create some folder
        folder_name = 'abc'
        vfs.mkdir(folder_name)
        assert vfs.exists(folder_name) is True

        # now, create a file
        fname = 'abc/sample.txt'
        fcontents = b'The quick brown dog jumps over the lazy fox'
        buffer = BytesIO(fcontents)
        vfs.write_file(buffer, fname)
        assert vfs.exists(fname) is True
        # remove file
        vfs.rmfile(fname)
        assert vfs.exists(fname) is False

        # test removing root
        with pytest.raises(VfsError):
            # attempt remove root dir
            vfs.rmfile('/')

        with pytest.raises(VfsError):
            # attempt remove root dir
            vfs.rmfile('.')

        # test removing folder
        with pytest.raises(VfsError):
            vfs.rmfile('abc')

        # test removing non-existing file
        with pytest.raises(VfsError):
            vfs.rmfile('abc/non-existing-file')

    def test_exists(self, volume):
        vfs = LocalVfs(volume)
        # create some folder
        folder_name = 'abc'
        assert vfs.exists(folder_name) is False
        vfs.mkdir(folder_name)
        assert vfs.exists(folder_name) is True

        # now, create a file
        fname = 'abc/sample.txt'
        fcontents = b'The quick brown dog jumps over the lazy fox'
        buffer = BytesIO(fcontents)
        vfs.write_file(buffer, fname)
        assert vfs.exists(fname) is True

        # remove file
        vfs.rmfile(fname)
        assert vfs.exists(fname) is False

    def test_chmod(self, volume):
        vfs = LocalVfs(volume)
        # create some folder
        folder_name = 'abc'
        vfs.mkdir(folder_name)
        assert vfs.exists(folder_name) is True

        # write bit should be on
        info = vfs.stat(folder_name)
        assert (info.permissions & stat.S_IWRITE) == stat.S_IWRITE
        orig_perms = info.permissions

        # lets turn it off
        perms = info.permissions & ~stat.S_IWRITE
        vfs.chmod(folder_name, perms)
        # check if it is off
        info = vfs.stat(folder_name)
        assert (info.permissions & stat.S_IWRITE) == 0
        # switch it back
        vfs.chmod(folder_name, orig_perms)

        with pytest.raises(VfsError):
            vfs.chmod('non-existing-file', perms)

    def test_get_local_file(self, volume):
        vfs = LocalVfs(volume)
        # create some folder
        folder_name = 'abc'
        assert vfs.exists(folder_name) is False
        vfs.mkdir(folder_name)
        # now, create a file
        fname = folder_name + '/sample.txt'
        fcontents = b'The quick brown dog jumps over the lazy fox'
        buffer = BytesIO(fcontents)
        vfs.write_file(buffer, fname)
        assert vfs.exists(fname) is True

        # get local file
        path = vfs.get_local_file(fname)
        assert path == volume.root / Path(path)
        # try to get non existing file
        with pytest.raises(VfsError):
            vfs.get_local_file('non-existing-file')

        # try to get folder
        with pytest.raises(VfsError):
            vfs.get_local_file('abc')

    def test_open_file(self, volume):
        vfs = LocalVfs(volume)
        # create some folder
        folder_name = 'abc'
        assert vfs.exists(folder_name) is False
        vfs.mkdir(folder_name)
        # now, create a file
        fname = folder_name + '/sample.txt'
        fcontents = b'The quick brown dog jumps over the lazy fox'
        buffer = BytesIO(fcontents)
        vfs.write_file(buffer, fname)
        assert vfs.exists(fname) is True

        # read file
        with vfs.open_file(fname) as fd:
            contents = fd.read()
            assert contents == fcontents

        # try to open non-existing file
        with pytest.raises(VfsError):
            vfs.open_file('non-existing-file')

    def test_read_file(self, volume):
        vfs = LocalVfs(volume)
        # create some folder
        folder_name = 'abc'
        assert vfs.exists(folder_name) is False
        vfs.mkdir(folder_name)
        # now, create a file
        fname = folder_name + '/sample.txt'
        fcontents = b'The quick brown dog jumps over the lazy fox'
        buffer = BytesIO(fcontents)
        vfs.write_file(buffer, fname)
        assert vfs.exists(fname) is True

        # read file
        contents = vfs.read_file(fname)
        assert fcontents == contents.getbuffer()

        # try to read non-existing file
        with pytest.raises(VfsError):
            vfs.read_file('non-existing-file')

    def test_read_file_text(self, volume):
        vfs = LocalVfs(volume)
        # create some folder
        folder_name = 'abc'
        assert vfs.exists(folder_name) is False
        vfs.mkdir(folder_name)
        # now, create a file
        fname = folder_name + '/sample.txt'
        fcontents = b'The quick brown dog jumps over the lazy fox'
        buffer = BytesIO(fcontents)
        vfs.write_file(buffer, fname)
        assert vfs.exists(fname) is True

        # read file
        contents = vfs.read_file_text(fname)
        assert str(fcontents, 'utf-8') == str(contents.read())

        # try to read non-existing file
        with pytest.raises(VfsError):
            vfs.read_file_text('non-existing-file')

    def test_add_file(self, volume):
        vfs = LocalVfs(volume)
        # create some folder
        folder_name = 'abc'
        assert vfs.exists(folder_name) is False
        vfs.mkdir(folder_name)

        # create local file
        fcontents = b'The quick brown dog jumps over the lazy fox'
        f = NamedTemporaryFile(delete=False)
        f.write(fcontents)
        f.close()

        # add to volume
        vfs.add_file(f.name, 'test.txt')
        os.unlink(f.name)
        contents = vfs.read_file_text('test.txt')
        assert str(contents.read()) == str(fcontents, 'utf-8')

        # try to add non-existing file
        with pytest.raises(VfsError):
            vfs.add_file('/tmp/add/non-existing-file', 'something.txt')

    def test_ls(self, volume):
        vfs = LocalVfs(volume)
        # create some folder
        folder_name = 'abc'
        assert vfs.exists(folder_name) is False
        vfs.mkdir(folder_name)
        # now, create a file
        fname = 'sample.txt'
        fcontents = b'The quick brown dog jumps over the lazy fox'
        buffer = BytesIO(fcontents)
        vfs.write_file(buffer, fname)
        assert vfs.exists(fname) is True

        flist = vfs.ls()
        folder_abc = None
        file_sample = None
        assert len(flist) == 2
        # extract file and folder
        if flist[0].is_dir:
            folder_abc = flist[0]
        else:
            file_sample = flist[0]

        if flist[1].is_dir:
            folder_abc = flist[1]
        else:
            file_sample = flist[1]

        # check folder info
        assert folder_abc.is_dir is True
        assert folder_abc.is_file is False
        assert folder_abc.object_name == 'abc'
        assert folder_abc.volume == str(volume.root)

        # check file info
        assert file_sample.is_dir is False
        assert file_sample.is_file is True
        assert file_sample.object_name == 'sample.txt'
        assert file_sample.content_type == 'text/plain'
        assert file_sample.size == 43
        assert file_sample.volume == str(volume.root)
