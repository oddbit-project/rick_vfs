# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Object-lock capability interfaces `VfsObjectLock` (per-object locking) and
  `VfsLockableVolume` (bucket lock configuration + versioning), implemented by
  `MinioVfs` and `MinioBucket` respectively. Backends can be introspected with
  `isinstance(vfs, VfsObjectLock)` / `isinstance(volume, VfsLockableVolume)`; the
  local backend implements neither.
- Per-object **legal hold**: `MinioVfs.enable_legal_hold`,
  `disable_legal_hold`, `legal_hold_enabled`.
- `MinioVfs.remove_object_bypass`: delete an object bypassing GOVERNANCE-mode
  retention (uses the bulk delete path; COMPLIANCE cannot be bypassed).
- Explicit `version_id` targeting on `stat`, `rmfile`, `read_file`,
  `read_file_text`, `get_object_retention`, `set_object_retention`.
- `MinioVfs.ls_versions`: list object versions (each item carries `version_id`
  and `is_latest`).

### Fixed

- `MinioObjectInfo.is_latest` was stored as the raw `'true'`/`'false'` string
  from minio version listings (so `'false'` evaluated truthy); it is now a real
  `bool`.
- `MinioVfs.get_object_retention` now returns `None` when no retention is set
  instead of raising.
- `MinioVfs.open_file`: the error-cleanup path referenced an unbound `fd` and
  called `.unlink()` on a `str`, crashing before the real error surfaced and
  leaking the temporary file. It now guards the descriptor and removes the temp
  file on every failure path.
- `MinioBucket.__init__`: an invalid SSE configuration constructed a
  `RuntimeError` without raising it. It now raises `VfsError`.
- `MinioVfs.mkdir`: minio's object-name validation raises `ValueError` (e.g. for
  `.`/`..` segments), which escaped the backend's error contract. It is now

- `MinioVfs.open_file`: the error-cleanup path referenced an unbound `fd` and
  called `.unlink()` on a `str`, crashing before the real error surfaced and
  leaking the temporary file. It now guards the descriptor and removes the temp
  file on every failure path.
- `MinioBucket.__init__`: an invalid SSE configuration constructed a
  `RuntimeError` without raising it. It now raises `VfsError`.
- `MinioVfs.mkdir`: minio's object-name validation raises `ValueError` (e.g. for
  `.`/`..` segments), which escaped the backend's error contract. It is now
  wrapped as `VfsError`.
- `VfsObjectInfo.attributes` was a shared mutable class attribute; it is now
  initialized per-instance in `MinioObjectInfo` and `LocalObjectInfo`.
- `read_file_text` (both backends): decode failures (`UnicodeDecodeError`,
  `LookupError`) are now wrapped as `VfsError`. The S3 implementation releases
  the connection before decoding so a decode error no longer leaks it.
- Removed an unreachable `except shutil.SameFileError` in `LocalVfs.add_file`
  (`SameFileError` subclasses `OSError`, already handled above).

### Changed

- **BREAKING:** `MinioBucket.root_path` is now a method instead of a
  `@property`, matching the `VfsVolume` contract and `LocalVolume`. Callers must
  use `volume.root_path()`.
- `MinioVfs.rmfile` now rejects directory keys (those ending in `/`) with
  `VfsError`, matching `LocalVfs.rmfile`'s file-only behavior. Use `rmdir()` for
  directories.
- `read_file_text` gains an `encoding` parameter (default `'utf-8'`) on both
  backends and the abstract `VfsContainer`, so non-UTF-8 text can be read.
- `MinioObjectInfo` now reads object metadata via the public `dict(src.metadata)`
  instead of the private `HTTPHeaderDict._container` attribute.
- `get_temp_dir` uses `uuid` instead of the private
  `tempfile._get_candidate_names()`.
- `MinioVfs.get_local_file` and `MinioVfs.open_file` reserve their temporary file
  with `tempfile.mkstemp()` instead of the deprecated `tempfile.mktemp()`.
- Corrected the `MinioBucket` SSE docstring example to use `SSEConfig` (bucket
  encryption) instead of `SseCustomerKey`.
- Test suite migrated from `tox-docker` to `testcontainers`: a session-scoped
  `MinioContainer` fixture replaces the externally managed MinIO, removing the
  hardcoded endpoint and credentials from the S3 tests. `tox.ini` and
  `requirements-dev.txt` updated accordingly.
- **BREAKING:** dropped Python 3.8 and 3.9 support. Minimum is now Python 3.10
  (`python_requires=">=3.10"`), driven by `testcontainers` 4.x. The CI/tox
  matrix and `setup.py` classifiers cover Python 3.10 through 3.14.
- Updated all dependencies to their latest releases (`minio` 7.2.20, `pytest` 9,
  `pytest-cov` 7.1, `coverage` 7.14, `flake8` 7.3, `flake8-black` 0.4, `tox`
  4.55, `testcontainers` 4.14, `mkdocs` 1.6, `mkdocs-material` 9.7).

### Removed

- `ordered_dict_to_dict` utility, including its global `copyreg` monkeypatch
  (not thread-safe); no longer used after the metadata change above.
- Unused `psycopg2-binary` development dependency.
- `tox-docker` dependency and the tox MinIO docker orchestration.
