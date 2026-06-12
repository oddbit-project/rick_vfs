import tempfile
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

import pytest
import urllib3
from minio.commonconfig import COMPLIANCE, GOVERNANCE, Tags
from minio.retention import Retention

from rick_vfs import VfsError, VfsObjectLock, VfsLockableVolume
from rick_vfs.local import LocalVfs, LocalVolume
from rick_vfs.s3 import MinioBucket, MinioVfs


@pytest.fixture()
def volume(minio_container):
    client = minio_container.get_client()
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


def _empty_locked_bucket(volume):
    """Fully empty a versioned/object-locked bucket: release holds and bypass-delete every version"""
    vfs = MinioVfs(volume)
    for item in vfs.ls_versions('', recursive=True):
        try:
            if vfs.legal_hold_enabled(item.object_name, version_id=item.version_id):
                vfs.disable_legal_hold(item.object_name, version_id=item.version_id)
        except VfsError:
            pass
        vfs.remove_object_bypass(item.object_name, version_id=item.version_id)


@pytest.fixture()
def locked_volume(minio_container):
    client = minio_container.get_client()
    volume = MinioBucket(client, 'test-bucket-lock', auto_create=False)
    if volume.exists():
        _empty_locked_bucket(volume)
        volume.remove()
    volume.create(object_lock=True)
    yield volume
    _empty_locked_bucket(volume)
    volume.remove()


@pytest.fixture()
def compliance_volume(minio_container):
    # dedicated bucket: COMPLIANCE-retained versions stay WORM-protected and cannot
    # be removed, so this fixture intentionally does not purge/remove on teardown
    # (the testcontainers MinIO is torn down at session end)
    client = minio_container.get_client()
    volume = MinioBucket(client, 'test-bucket-compliance', auto_create=False)
    if not volume.exists():
        volume.create(object_lock=True)
    yield volume


class TestMinioObjectLock:

    def test_capability_interfaces(self, volume):
        vfs = MinioVfs(volume)
        # s3 backend advertises both capabilities
        assert isinstance(vfs, VfsObjectLock)
        assert isinstance(volume, VfsLockableVolume)
        # local backend does not
        assert issubclass(LocalVfs, VfsObjectLock) is False
        assert issubclass(LocalVolume, VfsLockableVolume) is False

    def test_legal_hold(self, locked_volume):
        vfs = MinioVfs(locked_volume)
        file = 'test_legal_hold'
        vfs.write_file(BytesIO(b'locked contents'), file)
        vid = vfs.stat(file).version_id

        assert vfs.legal_hold_enabled(file) is False
        vfs.enable_legal_hold(file, version_id=vid)
        assert vfs.legal_hold_enabled(file, version_id=vid) is True

        # legal hold enforces WORM: the held version cannot be deleted
        with pytest.raises(VfsError):
            vfs.rmfile(file, version_id=vid)

        vfs.disable_legal_hold(file, version_id=vid)
        assert vfs.legal_hold_enabled(file, version_id=vid) is False

        # once the hold is released, the version can be deleted
        vfs.rmfile(file, version_id=vid)
        assert vid not in [v.version_id for v in vfs.ls_versions(file)]

    def test_retention(self, locked_volume):
        vfs = MinioVfs(locked_volume)
        file = 'test_retention'
        vfs.write_file(BytesIO(b'retained contents'), file)

        # no retention initially
        assert vfs.get_object_retention(file) is None

        until = datetime.now(timezone.utc) + timedelta(days=1)
        vfs.set_object_retention(file, Retention(GOVERNANCE, until))
        ret = vfs.get_object_retention(file)
        assert ret is not None
        assert ret.mode == GOVERNANCE

        # version-targeted retention round-trip
        vid = vfs.stat(file).version_id
        vfs.set_object_retention(file, Retention(GOVERNANCE, until), version_id=vid)
        ret_v = vfs.get_object_retention(file, version_id=vid)
        assert ret_v is not None
        assert ret_v.mode == GOVERNANCE

    def test_remove_object_bypass(self, locked_volume):
        vfs = MinioVfs(locked_volume)
        file = 'test_bypass'
        vfs.write_file(BytesIO(b'governance retained'), file)
        vid = vfs.stat(file).version_id
        until = datetime.now(timezone.utc) + timedelta(days=1)
        vfs.set_object_retention(file, Retention(GOVERNANCE, until))

        # version-targeted delete is blocked by governance retention
        with pytest.raises(VfsError):
            vfs.rmfile(file, version_id=vid)

        # bypass succeeds; the retained version is gone
        vfs.remove_object_bypass(file, version_id=vid)
        assert vid not in [v.version_id for v in vfs.ls_versions(file)]

    def test_compliance_cannot_be_bypassed(self, compliance_volume):
        vfs = MinioVfs(compliance_volume)
        file = 'test_compliance'
        vfs.write_file(BytesIO(b'compliance retained'), file)
        vid = vfs.stat(file).version_id
        until = datetime.now(timezone.utc) + timedelta(days=1)
        vfs.set_object_retention(file, Retention(COMPLIANCE, until), version_id=vid)

        # COMPLIANCE is strict WORM: neither a plain delete nor a governance bypass works
        with pytest.raises(VfsError):
            vfs.rmfile(file, version_id=vid)
        with pytest.raises(VfsError):
            vfs.remove_object_bypass(file, version_id=vid)
        # the version is still there
        assert vid in [v.version_id for v in vfs.ls_versions(file)]

    def test_versions(self, locked_volume):
        vfs = MinioVfs(locked_volume)
        file = 'test_versions'
        vfs.write_file(BytesIO(b'version one'), file)
        vfs.write_file(BytesIO(b'version two'), file)

        versions = vfs.ls_versions(file)
        assert len(versions) >= 2
        version_ids = [v.version_id for v in versions]
        # versions are distinct
        assert len(set(version_ids)) == len(version_ids)
        # exactly one is the latest
        latest = [v for v in versions if v.is_latest]
        assert len(latest) == 1

        # latest content is the second write
        assert vfs.read_file(file, version_id=latest[0].version_id).getbuffer() == b'version two'

        # version-targeted read of each version returns its own content
        contents = {str(vfs.read_file(file, version_id=v.version_id).getbuffer().tobytes(), 'utf-8')
                    for v in versions}
        assert contents == {'version one', 'version two'}

        # stat targets a specific (older) version
        older = [v for v in versions if not v.is_latest][0]
        assert vfs.stat(file, version_id=older.version_id).version_id == older.version_id

        # version-targeted text read
        assert vfs.read_file_text(file, version_id=latest[0].version_id).read() == 'version two'

        # version-targeted delete removes a single version
        vfs.rmfile(file, version_id=version_ids[0])
        remaining = [v.version_id for v in vfs.ls_versions(file)]
        assert version_ids[0] not in remaining
        assert len(remaining) == len(version_ids) - 1
