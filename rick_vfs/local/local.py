import os
import shutil
from datetime import datetime, timedelta
from io import BytesIO, StringIO
from pathlib import PurePath, Path
from typing import Union, Any, List

import magic

from rick_vfs.utils import dict_extract
from rick_vfs.vfs import VfsObjectInfo, VfsVolume, VfsContainer, VfsError


class LocalObjectInfo(VfsObjectInfo):

    def __init__(self, volume: PurePath, name: Path, src: os.stat_result):
        """
        Assemble object stat() information

        :param volume: the volume path
        :param name: absolute path for the object, including the volume
        :param src: os.stat() info
        """
        self.src = src
        self.object_name = name.name
        self.volume = str(volume)
        self.path = name
        if name.is_file():
            self.content_type = magic.from_file(name, mime=True)
        self.size = src.st_size
        self.atime = datetime.fromtimestamp(src.st_atime)
        self.mtime = datetime.fromtimestamp(src.st_mtime)
        self.owner_id = src.st_uid
        self.permissions = src.st_mode
        self.is_latest = True
        self.is_dir = name.is_dir()
        self.is_file = name.is_file()


class LocalVolume(VfsVolume):
    """
    LocalVolume allows the usage of a specific local folder path as virtual volume for VFS operations
    """

    def __init__(self, root_path: Union[str, Path], auto_create=True):
        """
        Initialize a local volume

        :param root_path: local root folder path for the volume
        :param auto_create: if True, the root folder path will be created if it doesn't exist
        """
        if isinstance(root_path, str):
            root_path = Path(root_path)

        if not isinstance(root_path, Path):
            raise VfsError("Invalid root path type")

        self.root = root_path.resolve()

        if auto_create:
            if not self.exists():
                self.create()

    def root_path(self) -> str:
        """
        Retrieve the root folder path as string
        :return: root folder path
        """
        return str(self.root)

    def exists(self) -> bool:
        """
        Check if volume root folder exists and is a valid directory
        :return: True if root folder exists, false otherwise
        """
        return self.root.exists() and self.root.is_dir()

    def create(self, **kwargs):
        """
        Create volume root folder path if it doesn't exist
        :param kwargs:
        :return:
        """
        if not self.root.exists():
            try:
                os.makedirs(self.root)
            except OSError as e:
                raise VfsError(e)
        else:
            if not self.root.is_dir():
                raise ValueError("Invalid root path '{}': not a directory".format(self.root))

    def remove(self, **kwargs):
        """
        Removes the local volume
        The volume folder must be empty
        :param kwargs:
        :return:
        """
        if self.exists():
            try:
                self.root.rmdir()
            except OSError as e:
                raise VfsError(e)

    def purge(self, **kwargs):
        """
        Removes the whole local volume directory tree
        This operation is not reversible, use with care - all data will be lost!
        :param kwargs:
        :return:
        """
        if self.exists():
            try:
                shutil.rmtree(self.root)
            except OSError as e:
                raise VfsError(e)

    def resolve_path(self, local_path: Union[str, Path]) -> Path:
        """
        Make path absolute and return the full volume path for the specified local path
        :param local_path: relative path inside the volume
        :return: Path object
        """
        return self.root / Path(os.path.relpath(os.path.normpath(os.path.join("/", local_path)), "/"))


class LocalVfs(VfsContainer):

    def __init__(self, volume: LocalVolume):
        self.volume = volume
        self.root = volume.root
        if not volume.exists():
            raise VfsError("Base path not found; volume not initialized?")

    def stat(self, object_name, **kwargs) -> Union[VfsObjectInfo, None]:
        """
        Get file or directory information

        :param object_name: object to get information

        :param kwargs:
        :return: VfsObjectInfo object with information, or None if object doesn't exist
        """
        path = self.volume.resolve_path(object_name)
        if not path.exists():
            return None
        try:
            return LocalObjectInfo(self.root, path, os.stat(path))
        except OSError as e:
            raise VfsError(e)

    def mkdir(self, directory_name, **kwargs) -> Any:
        """
        Creates a path or directory

        If directory_name is a non-existing path, it will be built

        :param directory_name: full path to create inside the volume
        :param kwargs:
        :return:
        """
        path = self.volume.resolve_path(directory_name)
        try:
            os.makedirs(path)
        except OSError as e:
            raise VfsError(e)

    def rmdir(self, directory_name, **kwargs) -> Any:
        """
        Removes an empty directory

        :param directory_name: full path of directory to remove
        :param kwargs:
        :return:
        """
        path = self.volume.resolve_path(directory_name)
        if path == self.root:
            raise VfsError("rmdir(): cannot remove root directory")
        try:
            path.rmdir()
        except OSError as e:
            raise VfsError(e)

    def rmfile(self, file_name, **kwargs) -> Any:
        """
        Removes a file

        :param file_name: full path to file to be removed
        :param kwargs:
        :return:
        """
        path = self.volume.resolve_path(file_name)
        if not path.is_file():
            raise VfsError("rmfile(): cannot remove '{}'; not a file".format(file_name))
        try:
            path.unlink()
        except OSError as e:
            raise VfsError(e)

    def exists(self, file_name, **kwargs) -> bool:
        """
        Check if a given path or file exists

        :param file_name: full path to verify
        :param kwargs:
        :return: True if exists, false otherwise
        """
        path = self.volume.resolve_path(file_name)
        return path.exists()

    def chmod(self, path, mask, **kwargs):
        """
        Posix chmod of files or folders

        :param path: full path for item to change permissions
        :param mask: permission mask
        :param kwargs:
        :return:
        """
        path = self.volume.resolve_path(path)
        if path == self.root:
            raise VfsError("chmod(): cannot change root folder permissions")
        try:
            os.chmod(path, mask)
        except OSError as e:
            raise VfsError(e)

    def chown(self, path, owner_id, group_id, **kwargs):
        """
        Posix chown of files or folders

        :param path: full path for item to change owner
        :param owner_id: owner id
        :param group_id: group id
        :param kwargs:
        :return:
        """
        path = self.volume.resolve_path(path)
        if path == self.root:
            raise VfsError("chown(): cannot change root folder owner")
        try:
            os.chown(path, owner_id, group_id)
        except OSError as e:
            raise VfsError(e)

    def get_local_file(self, file_name, **kwargs) -> Path:
        """
        Gets a full path for a locally accessible file

        :param file_name:
        :param kwargs:
        :return:
        """
        path = self.volume.resolve_path(file_name)
        if not path.is_file():
            raise VfsError("get_local_file(): file '{}' does not exist or is not a file".format(file_name))
        return path

    def open_file(self, file_name, **kwargs) -> Any:
        """
        Opens a locally-accessible file

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
        path = self.volume.resolve_path(file_name)
        if not path.is_file():
            raise VfsError("open_file(): file '{}' does not exist or is not a file".format(file_name))

        mode = dict_extract(kwargs, 'mode', 'rb')
        encoding = dict_extract(kwargs, 'encoding', None)
        newline = dict_extract(kwargs, 'newline', None)
        for key in ['mode', 'encoding', 'newline']:
            if key in kwargs.keys():
                del kwargs[key]

        try:
            # open file and return fd
            return open(str(path), mode=mode, encoding=encoding, newline=newline)

        except FileNotFoundError as e:
            raise VfsError(e)

        except BaseException as e:
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
        path = self.volume.resolve_path(file_name)
        if not path.is_file():
            raise VfsError("read_file(): file '{}' does not exist or is not a file".format(file_name))

        if length == 0:
            length = -1

        try:
            with open(path, 'rb') as f:
                f.seek(offset)
                result = BytesIO(f.read(length))
                result.seek(0)
                return result

        except FileNotFoundError as e:
            raise VfsError(e)

        except OSError as e:
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
        path = self.volume.resolve_path(file_name)
        if not path.is_file():
            raise VfsError("read_file_text(): file '{}' does not exist or is not a file".format(file_name))

        if length == 0:
            length = -1

        try:
            with open(path, 'rb') as f:
                f.seek(offset)
                result = StringIO(str(f.read(length), 'utf-8'))
                result.seek(0)
                return result

        except FileNotFoundError as e:
            raise VfsError(e)

        except OSError as e:
            raise VfsError(e)

    def url_file_get(self, file_name, expires=timedelta(hours=1), **kwargs) -> str:
        raise VfsError("url_file_get(): Unsupported operation on Local Volumes")

    def url_file_put(self, file_name, expires=timedelta(hours=1), **kwargs) -> str:
        raise VfsError("url_file_put(): Unsupported operation on Local Volumes")

    def write_file(self, buffer: BytesIO, file_name, **kwargs) -> Any:
        """
        Writes a binary buffer to a file

        If the file exists, it is rewritten

        :param buffer: buffer to write
        :param file_name: full path for destination file
        :param kwargs: optional parameters
        :return: None
        """
        path = self.volume.resolve_path(file_name)
        try:
            with open(path, 'wb') as f:
                buffer.seek(0)
                f.write(buffer.read())

        except FileNotFoundError as e:
            raise VfsError(e)

        except OSError as e:
            raise VfsError(e)

    def add_file(self, local_file, file_name, **kwargs) -> Any:
        """
        Adds a local file to the volume

        :param local_file: full path of source file
        :param file_name: full path for destination file
        :param kwargs: optional parameters
        :return: None
        """
        local_file = Path(local_file)
        path = self.volume.resolve_path(file_name)
        if not local_file.exists() or not local_file.is_file():
            raise VfsError("add_file(): invalid or non-existing local file")
        try:
            shutil.copyfile(local_file, path, follow_symlinks=True)
        except OSError as e:
            raise VfsError(e)
        except shutil.SameFileError as e:
            raise VfsError(e)

    def ls(self, path=Path('/'), **kwargs) -> List[LocalObjectInfo]:
        """
        List items on a given path

        Note: this is an intensive operation, because it fetches multiple details on the items
        Make sure you don't use this on huge folders

        :param path: path to scan
        :param kwargs:
        :return: List[LocalObjectInfo]
        """
        result = []
        path = self.volume.resolve_path(path)

        try:
            for item in os.listdir(path):
                fpath = path / Path(item)
                result.append(LocalObjectInfo(self.root, fpath, os.stat(fpath)))
            return result
        except OSError as e:
            raise VfsError(e)
