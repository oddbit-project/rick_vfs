import pytest
from testcontainers.minio import MinioContainer


@pytest.fixture(scope="session")
def minio_container():
    with MinioContainer() as container:
        yield container
