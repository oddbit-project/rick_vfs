import tempfile
from datetime import timedelta
from io import BytesIO, StringIO
from pathlib import PurePath, Path
from typing import List, Union, Any

import magic
from minio.commonconfig import Tags
from minio.helpers import check_bucket_name
from minio.lifecycleconfig import LifecycleConfig
from minio.objectlockconfig import ObjectLockConfig
from minio.retention import Retention
from minio.sseconfig import SSEConfig
from minio.versioningconfig import VersioningConfig

from minio import Minio, S3Error
from minio.datatypes import Object, Bucket

from rick_vfs.utils import ordered_dict_to_dict, dict_extract
from rick_vfs.vfs import VfsObjectInfo, VfsVolume, VfsError, VfsContainer


class MinioObjectInfo(VfsObjectInfo):
    is_local = False

    def __init__(self, src: Object):
        self.src = src
        self.object_name = src.object_name
        self.volume = src.bucket_name
        self.path = PurePath(src.object_name)
        self.content_type = src.content_type
        self.size = src.size
        # MiNIO doesnt have a create date attribute
        self.atime = src.last_modified
        self.mtime = src.last_modified
        self.owner_id = src.owner_id

        # private access to underlying OrderedDict of HTTPHeaderDict
        if src.metadata is not None:
            if getattr(src.metadata, '_container', None) is not None:
                self.attributes = ordered_dict_to_dict(src.metadata._container)
        self.etag = src.etag
        self.version_id = src.version_id
        self.is_latest = src.is_latest
        self.is_dir = src.is_dir
        self.is_file = not src.is_dir


class MinioBucket(VfsVolume):
    """
    MinioBucket allows the usage of a  MinIO/S3 bucket as root for VFS operations

        Example::
        # Create client with access key and secret key with specific region.
        client = Minio(
            "play.minio.io:9000",
            access_key="Q3AM3UQ867SPQQA43P2F",
            secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
            region="my-region",
        )

        # create volume with key-based encryption
        volume = MinioBucket(client, "my-bucket", sse=SseCustomerKey(b"32byteslongsecretkeymustprovided"))
    """

    def __init__(self, client: Minio, bucket_name, **kwargs):
        """
        Initialize minio volume

        By default, bucket will be created if it doesn't exist

        Optional arguments:
            sse - a valid Sse object to be used by the bucket
            auto_create (default True) - bucket will be created if it doesn't exist

        :param client: minio client
        :param bucket_name: bucket name
        :param kwargs: optional arguments (sse, auto_create)
        """
        check_bucket_name(bucket_name)
        self.client = client
        self.bucket_name = bucket_name
        self.sse = dict_extract(kwargs, 'sse')

        # sse options
        if self.sse is not None:
            if not isinstance(self.sse, SSEConfig):
                RuntimeError("Invalid SSE configuration")

        if dict_extract(kwargs, 'auto_create', True):
            if not self.exists():
                self.create(**kwargs)

    @property
    def root_path(self) -> str:
        return self.bucket_name

    def exists(self) -> bool:
        try:
            return self.client.bucket_exists(self.bucket_name)
        except S3Error as e:
            raise VfsError(e)

    def create(self, **kwargs):
        """
        Create a a bucket

        optional parameters:
        :param location: Region in which the bucket will be created.
        :param object_lock: Flag to set object-lock feature.
        """
        location = dict_extract(kwargs, 'location')
        object_lock = dict_extract(kwargs, 'object_lock', False)
        try:
            self.client.make_bucket(self.bucket_name, location, object_lock)
        except S3Error as e:
            raise VfsError(e)
        # apply encryption options
        if self.sse:
            self.set_encryption(self.sse)

    def remove(self, **kwargs):
        """
        Remove an existing bucket
        :return:
        """
        try:
            self.client.remove_bucket(self.bucket_name)
        except S3Error as e:
            raise VfsError(e)

    def purge(self, **kwargs):
        """
        Remove an existing bucket and all its contents

        This is a naive, non-threaded implementation, mostly suitable to cleanup test buckets; as such, using
        this in buckets with thousands of items or more will take a very long time

        :return:
        """
        try:
            # remove contents
            self._clean_dir('')
            # remove bucket
            self.remove()

        except S3Error as e:
            raise VfsError(e)

    def _clean_dir(self, path):
        try:
            path = str(path)
            if not path.endswith('/'):
                path = path + '/'
            for item in self.client.list_objects(self.bucket_name, path):
                if item.object_name != path:
                    if item.is_dir:
                        self._clean_dir(item.object_name)
                        self.client.remove_object(self.bucket_name, item.object_name)
                    else:
                        self.client.remove_object(self.bucket_name, item.object_name)
        except S3Error as e:
            raise VfsError(e)

    def list_buckets(self) -> List[Bucket]:
        """
        Return a list of available buckets
        :return: List of Bucket
        """
        try:
            return self.client.list_buckets()
        except S3Error as e:
            raise VfsError(e)

    def get_policy(self) -> str:
        try:
            return self.client.get_bucket_policy(self.bucket_name)
        except S3Error as e:
            raise VfsError(e)

    def set_policy(self, policy: str):
        try:
            self.client.set_bucket_policy(self.bucket_name, policy)
        except S3Error as e:
            raise VfsError(e)

    def remove_policy(self):
        try:
            self.client.delete_bucket_policy(self.bucket_name)
        except S3Error as e:
            raise VfsError(e)

    def set_encryption(self, config: SSEConfig):
        try:
            self.client.set_bucket_encryption(self.bucket_name, config)
        except S3Error as e:
            raise VfsError(e)

    def get_encryption(self) -> Union[SSEConfig, None]:
        try:
            return self.client.get_bucket_encryption(self.bucket_name)
        except S3Error as e:
            raise VfsError(e)

    def remove_encryption(self):
        try:
            self.client.delete_bucket_encryption(self.bucket_name)
        except S3Error as e:
            raise VfsError(e)

    def enable_versioning(self, mfa_delete=False):
        if not mfa_delete:
            mfa_delete = 'Disabled'
        else:
            mfa_delete = 'Enabled'
        try:
            self.client.set_bucket_versioning(self.bucket_name, VersioningConfig('Enabled', mfa_delete))
        except S3Error as e:
            raise VfsError(e)

    def disable_versioning(self):
        try:
            self.client.set_bucket_versioning(self.bucket_name, VersioningConfig('Suspended'))
        except S3Error as e:
            raise VfsError(e)

    def get_versioning(self) -> VersioningConfig:
        try:
            config = self.client.get_bucket_versioning(self.bucket_name)
            return config
        except S3Error as e:
            raise VfsError(e)

    def get_lifecycle(self) -> Union[LifecycleConfig, None]:
        try:
            return self.client.get_bucket_lifecycle(self.bucket_name)
        except S3Error as e:
            raise VfsError(e)

    def set_lifecycle(self, config: LifecycleConfig):
        try:
            self.client.set_bucket_lifecycle(self.bucket_name, config)
        except S3Error as e:
            raise VfsError(e)

    def remove_lifecycle(self):
        try:
            self.client.delete_bucket_lifecycle(self.bucket_name)
        except S3Error as e:
            raise VfsError(e)

    def set_tags(self, tags: Tags):
        try:
            self.client.set_bucket_tags(self.bucket_name, tags)
        except S3Error as e:
            raise VfsError(e)

    def get_tags(self) -> Union[Tags, None]:
        try:
            return self.client.get_bucket_tags(self.bucket_name)
        except S3Error as e:
            raise VfsError(e)

    def remove_tags(self):
        try:
            self.client.delete_bucket_tags(self.bucket_name)
        except S3Error as e:
            raise VfsError(e)

    def set_object_lock(self, config: ObjectLockConfig):
        try:
            self.client.set_object_lock_config(self.bucket_name, config)
        except S3Error as e:
            raise VfsError(e)

    def get_object_lock(self) -> Union[ObjectLockConfig, None]:
        try:
            return self.client.get_object_lock_config(self.bucket_name)
        except S3Error as e:
            if e.code == 'ObjectLockConfigurationNotFoundError':
                return None
            raise VfsError(e)

    def remove_object_lock(self):
        try:
            return self.client.delete_object_lock_config(self.bucket_name)
        except S3Error as e:
            raise VfsError(e)


class MinioVfs(VfsContainer):

    def __init__(self, volume: MinioBucket):
        self.volume = volume
        self.client = volume.client
        self.bucket_name = volume.bucket_name

    def stat(self, object_name, **kwargs) -> Union[VfsObjectInfo, None]:
        """
        Get file or directory information

        If object_name is a directory, it must end with '/'

        :param object_name:
        :param kwargs:
        :return:
        """
        try:
            info = self.client.stat_object(self.bucket_name, object_name, **kwargs)
            return MinioObjectInfo(info)
        except S3Error as e:
            if e.code == 'NoSuchKey':
                return None
            raise VfsError(e)

    def stat_dir(self, directory_name, **kwargs) -> Union[VfsObjectInfo, None]:
        """
        Get directory information

        This method ensures directory_name ends with '/' before calling stat()

        :param directory_name:
        :param kwargs:
        :return:
        """
        directory_name = str(directory_name)
        if not directory_name.endswith('/'):
            directory_name = str(directory_name) + '/'
        return self.stat(directory_name, **kwargs)

    def mkdir(self, directory_name, **kwargs) -> Any:
        try:
            directory_name = str(directory_name)
            if not directory_name.endswith('/'):
                directory_name = str(directory_name) + '/'
            return self.client.put_object(self.bucket_name, directory_name, length=0, data=BytesIO(b""), **kwargs)
        except S3Error as e:
            raise VfsError(e)

    def rmdir(self, directory_name, **kwargs) -> Any:
        """
        Removes a directory

        :param directory_name: full path for directory
        :param kwargs:
        :return:
        """
        try:
            directory_name = str(directory_name)
            if not directory_name.endswith('/'):
                directory_name = str(directory_name) + '/'
            info = self.client.stat_object(self.bucket_name, directory_name, **kwargs)
            if info is not None and info.is_dir:
                return self.client.remove_object(self.bucket_name, directory_name, **kwargs)
            else:
                raise VfsError("rmdir(): '{}' is not a directory".format(directory_name))
        except S3Error as e:
            raise VfsError(e)

    def rmfile(self, file_name, **kwargs) -> Any:
        """
        Removes an object from storage
        Note: this specific implementation can also remove directories

        :param file_name: full path for object to remove
        :param kwargs:
        :return: Object
        """
        try:
            file_name = str(file_name)
            return self.client.remove_object(self.bucket_name, file_name, **kwargs)
        except S3Error as e:
            raise VfsError(e)

    def exists(self, file_name, **kwargs) -> bool:
        """
        Check if a given object exists

        Directories must end with '/'

        :param file_name: full path for object to check
        :param kwargs:
        :return: True if object exists, false otherwise
        """
        try:
            file_name = str(file_name)
            info = self.client.stat_object(self.bucket_name, file_name, **kwargs)
            return info is not None
        except S3Error as e:
            if e.code == 'NoSuchKey':
                return False
            raise VfsError(e)

    def dir_exists(self, directory_name, **kwargs) -> bool:
        """
        Check if a given directory exists

        Alias to exists() that ensures that directory_name ends with '/'

        :param file_name: full path for directory to check
        :param kwargs:
        :return: True if object exists, false otherwise
        """
        directory_name = str(directory_name)
        if not directory_name.endswith('/'):
            directory_name = str(directory_name) + '/'
        return self.exists(directory_name, **kwargs)

    def chmod(self, path, mask, **kwargs):
        raise VfsError("chmod(): non-supported operation in current backend; use bucket policies instead")

    def chown(self, path, owner_id, group_id, **kwargs):
        raise VfsError("chown(): non-supported operation in current backend; use bucket policies instead")

    def get_local_file(self, file_name, **kwargs) -> Path:
        """
        Creates a local copy of a remote file

        The local temporary file must be removed manually

        :param file_name: full path for the object to fetch
        :param kwargs: optional fetch parameters
        :return: Path() object to the temporary file
        """
        # generate temp file name
        tmp_file = tempfile.mktemp()
        try:
            file_name = str(file_name)
            # fetch from server to temp file
            _ = self.client.fget_object(self.bucket_name, file_name, tmp_file, **kwargs)
            return Path(tmp_file)
        except S3Error as e:
            raise VfsError(e)

    def open_file(self, file_name, **kwargs) -> Any:
        """
        Opens a locally-accessible file copy from the server

        Note: The temporary local file is automatically deleted when the file is closed

        file-related kwargs:
            :param mode: file access mode (default 'rb')
            :param encoding: file encoding (default None)
            :paramm newline: end-of-line marker (default None)

        Example::
            try:
                with vfs.open_file('my-file') as f:
                    f.read()
            except:
                raise

        :param file_name: full path from the object to retrieve
        :param kwargs: optional arguments
        :return: Path() object to the local file
        """
        mode = dict_extract(kwargs, 'mode', 'rb')
        encoding = dict_extract(kwargs, 'encoding', None)
        newline = dict_extract(kwargs, 'newline', None)
        for key in ['mode', 'encoding', 'newline']:
            if key in kwargs.keys():
                del kwargs[key]

        # generate temp file name
        tmp_file = tempfile.mktemp()
        try:
            file_name = str(file_name)
            # fetch from server to temp file
            _ = self.client.fget_object(self.bucket_name, file_name, tmp_file, **kwargs)

            # open temp file
            fd = open(tmp_file, mode=mode, encoding=encoding, newline=newline)

            # use internal tempfile wrapper to provide automatic deletion on closing
            return tempfile._TemporaryFileWrapper(fd, tmp_file)

        except S3Error as e:
            raise VfsError(e)

        except BaseException as e:
            fd.close()
            tmp_file.unlink()
            raise VfsError(e)

    def read_file(self, file_name, offset=0, length=0, **kwargs) -> BytesIO:
        """
        Reads a binary file to a memory buffer

        :param file_name: full file path to read
        :param offset: optional start offset
        :param length: optional length
        :param kwargs: optional parameters
        :return: BytesIO buffer
        """
        try:
            file_name = str(file_name)
            response = self.client.get_object(self.bucket_name, file_name, offset=offset, length=length, **kwargs)
            result = BytesIO(response.read())
            response.close()
            response.release_conn()
            result.seek(0)
            return result

        except S3Error as e:
            raise VfsError(e)

    def read_file_text(self, file_name, offset=0, length=0, **kwargs) -> StringIO:
        """
        Reads a text file to a memory buffer

        :param file_name: full file path to read
        :param offset: optional start offset
        :param length: optional length
        :param kwargs: optional parameters
        :return: BytesIO buffer
        """
        try:
            file_name = str(file_name)
            response = self.client.get_object(self.bucket_name, file_name, offset=offset, length=length, **kwargs)
            result = StringIO(str(response.read(), 'utf-8'))
            response.close()
            response.release_conn()
            result.seek(0)
            return result

        except S3Error as e:
            raise VfsError(e)

    def url_file_get(self, file_name, expires=timedelta(hours=1), **kwargs) -> str:
        """
        Get a presigned URL to download the specified file from the server

        :param file_name: full path to the file
        :param expires: timedelta from current time
        :param kwargs: optional args
        :return: url to download the file
        """
        try:
            file_name = str(file_name)
            return self.client.get_presigned_url('GET', self.bucket_name, file_name, expires=expires, **kwargs)

        except S3Error as e:
            raise VfsError(e)

    def url_file_put(self, file_name, expires=timedelta(hours=1), **kwargs) -> str:
        """
        Get a presigned URL to upload a file to the server

        :param file_name: full path to the file to be created
        :param expires: timedelta from current time
        :param kwargs: optional args
        :return: url to download the file
        """
        try:
            file_name = str(file_name)
            return self.client.get_presigned_url('PUT', self.bucket_name, file_name, expires=expires, **kwargs)

        except S3Error as e:
            raise VfsError(e)

    def write_file(self, buffer: BytesIO, file_name, **kwargs) -> Any:
        """
        Writes a binary buffer to a file
        :param buffer: buffer to write
        :param file_name: full path for new object
        :param kwargs: optional parameters
        :return: ObjectWriteResult object
        """
        try:
            file_name = str(file_name)
            content_type = magic.from_buffer(buffer.getbuffer().tobytes(), mime=True)
            buffer.seek(0)
            return self.client.put_object(self.bucket_name, file_name, buffer, buffer.getbuffer().nbytes,
                                          content_type=content_type, **kwargs)
        except S3Error as e:
            raise VfsError(e)

    def add_file(self, local_file, file_name, **kwargs) -> Any:
        """
        Adds a local file to Minio

        :param local_file: full path of source file
        :param file_name: full path for object
        :param kwargs: optional parameters
        :return: ObjectWriteResult object
        """
        local_file = Path(local_file)
        if not local_file.exists() or not local_file.is_file():
            raise VfsError("add_file(): invalid or non-existing local file")
        try:
            file_name = str(file_name)
            content_type = magic.from_file(local_file, mime=True)
            return self.client.fput_object(self.bucket_name, file_name, local_file, content_type=content_type, **kwargs)
        except S3Error as e:
            raise VfsError(e)

    def get_tags(self, object_name, **kwargs) -> Tags:
        """
        Get object tags

        :param object_name: full path for object
        :param kwargs:
        :return: Tags object
        """
        try:
            object_name = str(object_name)
            return self.client.get_object_tags(self.bucket_name, object_name, **kwargs)
        except S3Error as e:
            raise VfsError(e)

    def set_tags(self, object_name, tags: Tags, **kwargs):
        """
        Set object tags

        :param object_name: full path for object
        :param tags: Tags object
        :param kwargs:
        :return: None
        """
        try:
            self.client.set_object_tags(self.bucket_name, object_name, tags, **kwargs)
        except S3Error as e:
            raise VfsError(e)

    def remove_tags(self, object_name, **kwargs):
        """
        Remove object tags

        :param object_name: full path for object
        :param kwargs:
        :return: None
        """
        try:
            object_name = str(object_name)
            self.client.delete_object_tags(self.bucket_name, object_name, **kwargs)
        except S3Error as e:
            raise VfsError(e)

    def get_object_retention(self, object_name, **kwargs) -> Retention:
        """
        Get object retention policy

        :param object_name: full path for object
        :param kwargs:
        :return: Retention
        """
        try:
            object_name = str(object_name)
            return self.client.get_object_retention(self.bucket_name, object_name, **kwargs)
        except S3Error as e:
            raise VfsError(e)

    def set_object_retention(self, object_name, retention: Retention, **kwargs):
        """
        Set object retention policy

        :param object_name: full path for object
        :param retention: Retention object
        :param kwargs:
        :return: None
        """
        try:
            object_name = str(object_name)
            self.client.set_object_retention(self.bucket_name, object_name, retention, **kwargs)
        except S3Error as e:
            raise VfsError(e)

    def ls(self, path=Path('/'), **kwargs) -> List[MinioObjectInfo]:
        """
        List contents of the given path

        Wildcards ('*') are not supported; instead, to fetch all objects that start with eg. 'x', use '/some/path/x' as path

        :param path: path to search
        :param kwargs: optional parameters
        :return: List[MinioObjectInfo]
        """
        result = []
        try:
            path = str(path)
            for item in self.client.list_objects(self.bucket_name, prefix=path, **kwargs):
                result.append(MinioObjectInfo(item))
            return result
        except S3Error as e:
            raise VfsError(e)
