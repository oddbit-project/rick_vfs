# Object lock & versioning (S3 backend)

The S3/MinIO backend supports the full set of S3 object-lock primitives: bucket-level
lock configuration, versioning, per-object retention (GOVERNANCE / COMPLIANCE),
legal hold, governance-bypass deletion and version-targeted operations.

These features are specific to the S3 backend; the local backend does not implement
them.

## Capability detection

Lock support is exposed through two capability interfaces so a backend can be
introspected with `isinstance()`:

- `VfsObjectLock` — per-object locking (implemented by `MinioVfs`)
- `VfsLockableVolume` — bucket lock configuration and versioning (implemented by `MinioBucket`)

```python
from rick_vfs import VfsObjectLock, VfsLockableVolume

if isinstance(vfs, VfsObjectLock):
    vfs.enable_legal_hold("my-object")

if isinstance(volume, VfsLockableVolume):
    volume.enable_versioning()
```

The local backend (`LocalVfs` / `LocalVolume`) is not an instance of either interface.

## Enabling object lock

Object lock must be enabled when the bucket is created, and it automatically enables
versioning:

```python
from minio import Minio
from rick_vfs.s3 import MinioBucket, MinioVfs

client = Minio("localhost:9010", secure=False,
               access_key="user", secret_key="password")

# create a lock-enabled (and therefore versioned) bucket
volume = MinioBucket(client, "my-bucket", object_lock=True)
vfs = MinioVfs(volume)
```

An optional default retention rule can be configured on the bucket:

```python
from minio.commonconfig import GOVERNANCE
from minio.objectlockconfig import ObjectLockConfig, DAYS

volume.set_object_lock(ObjectLockConfig(GOVERNANCE, 30, DAYS))
config = volume.get_object_lock()   # None if no rule is set
volume.remove_object_lock()
```

## Versioning

```python
volume.enable_versioning()
volume.disable_versioning()
volume.get_versioning().status      # 'Enabled' | 'Suspended'
```

## Legal hold

A legal hold is an on/off WORM flag with no expiry. While it is enabled the object
version cannot be deleted.

```python
vfs.enable_legal_hold("my-object")
vfs.legal_hold_enabled("my-object")   # True
vfs.disable_legal_hold("my-object")
```

## Retention

Retention protects a specific object version until a date, in one of two modes:

- `GOVERNANCE` — can be bypassed by a principal with the `s3:BypassGovernanceRetention` permission
- `COMPLIANCE` — strict WORM; cannot be shortened or bypassed by anyone until it expires

```python
from datetime import datetime, timedelta, timezone
from minio.commonconfig import GOVERNANCE
from minio.retention import Retention

until = datetime.now(timezone.utc) + timedelta(days=7)
vfs.set_object_retention("my-object", Retention(GOVERNANCE, until))

ret = vfs.get_object_retention("my-object")   # None if no retention is set
ret.mode             # 'GOVERNANCE'
```

## Governance-bypass deletion

A normal `rmfile()` cannot delete a version that is under GOVERNANCE retention.
`remove_object_bypass()` deletes it, bypassing the retention (requires the
`s3:BypassGovernanceRetention` permission). COMPLIANCE retention cannot be bypassed.

```python
vfs.remove_object_bypass("my-object", version_id="…")
```

## Versions

Every object operation accepts an explicit `version_id`, and `ls_versions()` lists the
versions of a key (each item carries `version_id` and `is_latest`):

```python
for item in vfs.ls_versions("my-object"):
    print(item.version_id, item.is_latest)

data = vfs.read_file("my-object", version_id="…")
info = vfs.stat("my-object", version_id="…")
vfs.rmfile("my-object", version_id="…")
```
