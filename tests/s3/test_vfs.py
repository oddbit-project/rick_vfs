import tempfile
from io import BytesIO
from pathlib import Path

import pytest
import urllib3
from minio import Minio
from minio.commonconfig import Tags

from rick_vfs import VfsError
from rick_vfs.s3 import MinioBucket, MinioVfs


@pytest.fixture()
def volume():
    client = Minio(
        "localhost:9010",
        secure=False,
        access_key="SomeTestUser",
        secret_key="SomeTestPassword",
    )
    volume = MinioBucket(client, 'test-bucket-vfs')
    # recycle bucket
    volume.purge()
    volume.create()
    yield volume
    volume.purge()


class TestMinioVFS:

    def test_init(self, volume):
        vfs = MinioVfs(volume)
        assert vfs.volume == volume
        assert vfs.client == volume.client
        assert vfs.bucket_name == volume.bucket_name

    def test_mkdir(self, volume):
        vfs = MinioVfs(volume)
        folder = 'test_mkdir'
        assert vfs.dir_exists(folder) is False
        vfs.mkdir(folder)
        assert vfs.dir_exists(folder) is True
        vfs.rmdir(folder)

        folder = 'test_mkdir_2/other_folder'
        assert vfs.dir_exists(folder) is False
        vfs.mkdir(folder)
        assert vfs.dir_exists(folder) is True
        vfs.rmdir(folder)

        # attempt to create root
        with pytest.raises(VfsError):
            vfs.mkdir('/')
        with pytest.raises(VfsError):
            vfs.mkdir('')
        # attempt to create folder with invalid name
        with pytest.raises(VfsError):
            vfs.mkdir('.')

    def test_rmdir(self, volume):
        vfs = MinioVfs(volume)
        folder = 'test_rmdir'
        vfs.mkdir(folder)
        assert vfs.dir_exists(folder) is True
        vfs.rmdir(folder)
        assert vfs.dir_exists(folder) is False

        file = 'test_rmdir_file'
        buf = BytesIO(b'the quick brown fox jumps over the lazy dog')
        vfs.write_file(buf, file)
        assert vfs.exists(file) is True
        with pytest.raises(VfsError):
            vfs.rmdir(file)
        vfs.rmfile(file)

        with pytest.raises(VfsError):
            vfs.rmdir('/')
        with pytest.raises(VfsError):
            vfs.rmdir('')

    def test_get_local_file(self, volume):
        vfs = MinioVfs(volume)

        file = 'test_local_file'
        buf = BytesIO(b'the quick brown fox jumps over the lazy dog')
        vfs.write_file(buf, file)
        assert vfs.exists(file) is True

        local_file = vfs.get_local_file(file)
        assert local_file.exists()
        assert local_file.is_file()
        with open(local_file, 'rb') as f:
            assert f.read() == buf.getbuffer()

    def test_open_file(self, volume):
        vfs = MinioVfs(volume)

        file = 'test_local_file'
        buf = BytesIO(b'the quick brown fox jumps over the lazy dog')
        vfs.write_file(buf, file)
        assert vfs.exists(file) is True

        # test open file without context
        fd = vfs.open_file(file)
        assert fd is not None
        assert fd.read() == buf.getbuffer()
        fname = Path(fd.name)
        assert fname.exists() is True
        fd.close()  # closes & REMOVES file
        assert fname.exists() is False

        # test open file with "with"
        fname = None
        with vfs.open_file(file) as f:
            assert f.read() == buf.getbuffer()
            fname = Path(f.name)
        # file automatically closed & removed
        assert fname.exists() is False

    def test_read_file(self, volume):
        vfs = MinioVfs(volume)

        file = 'test_local_file'
        buf = BytesIO(b'the quick brown fox jumps over the lazy dog')
        vfs.write_file(buf, file)
        assert vfs.exists(file) is True

        assert vfs.read_file(file, length=3).getbuffer() == b'the'
        assert vfs.read_file(file, offset=4, length=5).getbuffer() == b'quick'
        assert vfs.read_file(file).getbuffer() == buf.getbuffer()

    def test_read_file_text(self, volume):
        vfs = MinioVfs(volume)

        file = 'test_local_file'
        buf = BytesIO(b'the quick brown fox jumps over the lazy dog')
        vfs.write_file(buf, file)
        assert vfs.exists(file) is True

        assert vfs.read_file_text(file, length=3).getvalue() == 'the'
        assert vfs.read_file_text(file, offset=4, length=5).getvalue() == 'quick'
        assert vfs.read_file_text(file).getvalue() == str(buf.getbuffer(), 'utf-8')

    def test_url_file_get(self, volume):
        vfs = MinioVfs(volume)

        file = 'test_url_file_get'
        buf = BytesIO(b'the quick brown fox jumps over the lazy dog')
        vfs.write_file(buf, file)
        assert vfs.exists(file) is True

        url = vfs.url_file_get(file)
        assert type(url) is str
        assert len(url) > 0

        http = urllib3.PoolManager()
        r = http.request('GET', url)
        assert r.status == 200
        assert r.data == buf.getbuffer()

    def test_url_file_put(self, volume):
        vfs = MinioVfs(volume)

        file = 'test_url_file_put'
        contents = b'the quick brown fox jumps over the lazy dog'
        url = vfs.url_file_put(file)
        http = urllib3.PoolManager()
        r = http.request('PUT', url, body=contents)
        assert r.status == 200
        assert vfs.exists(file) is True
        assert vfs.read_file(file).getbuffer() == contents

    def test_write_file(self, volume):
        vfs = MinioVfs(volume)

        file = 'test_write_file'
        buf = BytesIO(b'the quick brown fox jumps over the lazy dog')
        vfs.write_file(buf, file)
        assert vfs.exists(file) is True

    def test_add_file(self, volume):
        vfs = MinioVfs(volume)

        file = 'test_add_file'
        buf = BytesIO(b'the quick brown fox jumps over the lazy dog')
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(buf.getbuffer().tobytes())
        tmp.close()
        assert Path(tmp.name).exists() is True

        vfs.add_file(tmp.name, file)
        assert vfs.read_file(file).getbuffer() == buf.getbuffer()

    def test_get_set_tags(self, volume):
        vfs = MinioVfs(volume)

        file = 'test_tags'
        buf = BytesIO(b'the quick brown fox jumps over the lazy dog')
        vfs.write_file(buf, file)
        assert vfs.exists(file) is True

        tags = vfs.get_tags(file)
        assert tags is None
        tags = Tags()
        for i in range(1, 5):
            tags['tag' + str(i)] = "this is tag " + str(i)
        vfs.set_tags(file, tags)

        # read tags
        read_tags = vfs.get_tags(file)
        assert read_tags is not None
        assert len(read_tags) == len(tags)
        for k, v in read_tags.items():
            assert k in tags.keys()
            assert v == tags[k]

        vfs.remove_tags(file)
        tags = vfs.get_tags(file)
        assert tags is None

    def test_ls(self, volume):
        vfs = MinioVfs(volume)

        file = 'test_ls'
        buf = BytesIO(b'the quick brown fox jumps over the lazy dog')
        vfs.write_file(buf, file)
        assert vfs.exists(file) is True

        vfs.mkdir('folder1/folder2')
        names_list = []
        for item in vfs.ls():
            names_list.append(item.object_name)
        for k in ['folder1/', 'test_ls']:
            assert k in names_list

        names_list = []
        for item in vfs.ls('folder1/'):
            names_list.append(item.object_name)
        for k in ['folder1/folder2/']:
            assert k in names_list
