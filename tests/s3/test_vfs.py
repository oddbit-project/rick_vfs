import pytest
from minio import Minio
from minio.sseconfig import SSEConfig, Rule as SSERule

from rick_vfs.s3 import MinioBucket, MinioVfs

SSE_CONFIG = SSEConfig(SSERule.new_sse_s3_rule())


@pytest.fixture()
def client():
    client = Minio(
        "localhost:9010",
        secure=False,
        access_key="SomeTestUser",
        secret_key="SomeTestPassword",
    )
    return MinioBucket(client, 'test-bucket-vfs')


class TestMinioVFS:

    def test_init(self, volume):
        vfs = MinioVfs(volume)
        assert vfs.volume == volume
        assert vfs.client == volume.client
        assert vfs.bucket_name == volume.bucket_name

