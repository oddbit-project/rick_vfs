# rick-vfs

Minio/S3 client VFS abstraction library

[![Tests](https://github.com/oddbit-project/rick_vfs/workflows/Tests/badge.svg?branch=master)](https://github.com/oddbit-project/rick_vfs/actions)
[![pypi](https://img.shields.io/pypi/v/rick_vfs.svg)](https://pypi.org/project/rick-vfs/)
[![license](https://img.shields.io/pypi/l/rick_vfs.svg)](https://git.oddbit.org/OddBit/rick_vfs/src/branch/master/LICENSE)

Rick-vfs is a high-level abstraction library for file operations on local repositories (a locally accessible folder) and 
Minio/S3 object storage systems. The main goal is to provide a set of common interface functions with analogous behaviour,
to interact with both scenarios.

The intention of "analogous behaviour" is to mimick overall intent and response type, when possible. There will always
be differences between invoking a given method on two different backends.



Example:
```python
from io import BytesIO
from minio import Minio
from rick_vfs.s3 import MinioBucket, MinioVfs

client = Minio(
    "localhost:9010",
    secure=False,
    access_key="SomeTestUser",
    secret_key="SomeTestPassword",
)

# initialize bucket
volume = MinioBucket(client, 'my-bucket')
# initialize VFS object
vfs = MinioVfs(volume)

# create directory
vfs.mkdir("contents/files")

# create file from buffer
buf = BytesIO(b'the quick brown fox jumps over the lazy dog')
vfs.write_file(buf, 'contents/files/my_test_file')

# read file
contents = vfs.read_file('my_test_file')
# print contents
print(str(contents.getbuffer().tobytes(), 'utf-8'))

# list bucket contents
print("Bucket contents:")
for item in vfs.ls():
    print(item.object_name)
```
