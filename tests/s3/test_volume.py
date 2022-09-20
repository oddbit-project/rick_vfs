import pytest
from minio import Minio

from rick_vfs.s3 import MinioBucket

TEST_BUCKET = 'test-bucket'


@pytest.fixture()
def client():
    client = Minio(
        "localhost:9010",
        secure=False,
        access_key="SomeTestUser",
        secret_key="SomeTestPassword",
    )
    return client


class TestMinioVolume:

    def test_init(self, client):
        volume = MinioBucket(client, TEST_BUCKET)
        assert volume.exists() is True
        assert volume.bucket_name == TEST_BUCKET
        assert volume.sse is None
