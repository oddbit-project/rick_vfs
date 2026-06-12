import abc
from datetime import datetime, timedelta
from io import BytesIO, StringIO
from pathlib import PurePath, Path
from typing import Any, Union


class VfsError(Exception):
    """ Global VFS Error Exception"""


class VfsObjectInfo:
    is_local = True
    object_name = ''
    volume = ''
    path = None  # type: PurePath
    content_type = ''
    size = 0
    atime = None  # type: datetime.datetime
    mtime = None  # type: datetime.datetime
    owner_id = 0
    permissions = 0
    attributes = {}
    src = None
    etag = ''
    is_dir = False
    is_file = False
    version_id = None
    is_latest = True


class VfsContainer(abc.ABC):

    @abc.abstractmethod
    def stat(self, object_name, **kwargs) -> Union[VfsObjectInfo, None]:
        pass

    @abc.abstractmethod
    def mkdir(self, directory_name, **kwargs) -> Any:
        pass

    @abc.abstractmethod
    def rmdir(self, directory_name, **kwargs) -> Any:
        pass

    @abc.abstractmethod
    def rmfile(self, file_name, **kwargs) -> Any:
        pass

    @abc.abstractmethod
    def exists(self, file_name, **kwargs) -> bool:
        pass

    @abc.abstractmethod
    def chmod(self, path, mask, **kwargs):
        pass

    @abc.abstractmethod
    def chown(self, path, owner_id, group_id, **kwargs):
        pass

    @abc.abstractmethod
    def get_local_file(self, file_name, **kwargs) -> Path:
        pass

    @abc.abstractmethod
    def open_file(self, file_name, **kwargs) -> Any:
        pass

    @abc.abstractmethod
    def read_file(self, file_name, offset=0, length=0, **kwargs) -> BytesIO:
        pass

    @abc.abstractmethod
    def read_file_text(self, file_name, offset=0, length=0, encoding='utf-8', **kwargs) -> StringIO:
        pass

    @abc.abstractmethod
    def url_file_get(self, file_name, expires=timedelta(hours=1), **kwargs) -> str:
        pass

    @abc.abstractmethod
    def url_file_put(self, file_name, expires=timedelta(hours=1), **kwargs) -> str:
        pass

    @abc.abstractmethod
    def write_file(self, buffer: BytesIO, file_name, **kwargs) -> Any:
        pass

    @abc.abstractmethod
    def add_file(self, local_file, file_name, **kwargs) -> Any:
        pass


class VfsVolume(abc.ABC):

    @abc.abstractmethod
    def root_path(self) -> str:
        pass

    @abc.abstractmethod
    def exists(self) -> bool:
        pass

    @abc.abstractmethod
    def create(self, **kwargs):
        pass

    @abc.abstractmethod
    def remove(self, **kwargs):
        pass

    @abc.abstractmethod
    def purge(self, **kwargs):
        pass


class VfsLockableVolume(abc.ABC):
    """Capability interface: volume supports object-lock configuration and versioning"""

    @abc.abstractmethod
    def set_object_lock(self, config):
        pass

    @abc.abstractmethod
    def get_object_lock(self):
        pass

    @abc.abstractmethod
    def remove_object_lock(self):
        pass

    @abc.abstractmethod
    def enable_versioning(self, mfa_delete=False):
        pass

    @abc.abstractmethod
    def disable_versioning(self):
        pass

    @abc.abstractmethod
    def get_versioning(self):
        pass


class VfsObjectLock(abc.ABC):
    """Capability interface: container supports per-object locking"""

    @abc.abstractmethod
    def enable_legal_hold(self, object_name, version_id=None, **kwargs):
        pass

    @abc.abstractmethod
    def disable_legal_hold(self, object_name, version_id=None, **kwargs):
        pass

    @abc.abstractmethod
    def legal_hold_enabled(self, object_name, version_id=None, **kwargs) -> bool:
        pass

    @abc.abstractmethod
    def get_object_retention(self, object_name, version_id=None, **kwargs):
        pass

    @abc.abstractmethod
    def set_object_retention(self, object_name, retention, version_id=None, **kwargs):
        pass

    @abc.abstractmethod
    def remove_object_bypass(self, object_name, version_id=None, **kwargs):
        pass