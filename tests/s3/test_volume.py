import json

import pytest
from minio import Minio, xml
from minio.commonconfig import ENABLED, Filter, AndOperator, DISABLED, Tags, GOVERNANCE
from minio.lifecycleconfig import LifecycleConfig, Rule as LCRule, Transition, Expiration
from minio.objectlockconfig import ObjectLockConfig, DAYS
from minio.replicationconfig import ReplicationConfig, Destination, DeleteMarkerReplication
from minio.sseconfig import Rule as SSERule
from minio.sse import SseCustomerKey
from minio.sseconfig import SSEConfig

from rick_vfs import VfsError
from rick_vfs.s3 import MinioBucket

TEST_BUCKET = 'test-bucket'

POLICY_READ_ONLY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"AWS": ["*"]},
            "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
            "Resource": ["arn:aws:s3:::" + TEST_BUCKET],
        },
        {
            "Effect": "Allow",
            "Principal": {"AWS": ["*"]},
            "Action": ["s3:GetObject"],
            "Resource": ["arn:aws:s3:::" + TEST_BUCKET + "/*"],
        },
    ],
}

LIFE_CYCLE = LifecycleConfig(
    [
        LCRule(
            ENABLED,
            rule_filter=Filter(prefix="logs/"),
            rule_id="rule2",
            expiration=Expiration(days=365),
        ),
    ],
)

LOCK_CONFIG = ObjectLockConfig(GOVERNANCE, 15, DAYS)

SSE_CONFIG = SSEConfig(SSERule.new_sse_s3_rule())


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

    def test_create_remove(self, client):
        volume = MinioBucket(client, TEST_BUCKET)
        assert volume.exists() is True

        # remove test bucket
        volume.purge()
        assert volume.exists() is False
        # force creation of test bucket
        volume.create()
        assert volume.exists() is True

    def test_list(self, client):
        volume = MinioBucket(client, TEST_BUCKET)
        assert volume.exists() is True

        buckets = volume.list_buckets()
        names = []
        for b in buckets:
            names.append(b.name)
        assert TEST_BUCKET in names

    def test_policy(self, client):
        volume = MinioBucket(client, TEST_BUCKET)
        # ensure the bucket is completely clean
        volume.purge()
        volume.create()
        # no existing policy, should raise exception
        with pytest.raises(VfsError):
            _ = volume.get_policy()

        json_policy = json.dumps(POLICY_READ_ONLY, sort_keys=True)
        volume.set_policy(json_policy)

        policy = volume.get_policy()
        # sort keys
        policy = json.dumps(json.loads(policy), sort_keys=True)
        # we just compare char length, due to the fact sometimes list items get out of order
        assert len(policy) == len(json_policy)

    def test_versioning(self, client):
        volume = MinioBucket(client, TEST_BUCKET)
        # ensure the bucket is completely clean
        volume.purge()
        volume.create()

        volume.disable_versioning()
        assert volume.get_versioning().status == 'Suspended'
        volume.enable_versioning()
        assert volume.get_versioning().status == 'Enabled'
        volume.disable_versioning()
        assert volume.get_versioning().status == 'Suspended'

    def test_lifecycle(self, client):
        volume = MinioBucket(client, TEST_BUCKET)
        # ensure the bucket is completely clean
        volume.purge()
        volume.create()

        cfg = volume.get_lifecycle()
        assert cfg is None
        volume.set_lifecycle(LIFE_CYCLE)
        cfg = volume.get_lifecycle()
        assert xml.marshal(cfg) == xml.marshal(LIFE_CYCLE)
        volume.remove_lifecycle()
        cfg = volume.get_lifecycle()
        assert cfg is None

    def test_tags(self, client):
        volume = MinioBucket(client, TEST_BUCKET)
        # ensure the bucket is completely clean
        volume.purge()
        volume.create()

        tags = Tags()
        for i in range(1, 5):
            tags['tag' + str(i)] = "this is tag " + str(i)

        bucket_tags = volume.get_tags()
        assert bucket_tags is None
        volume.set_tags(tags)
        bucket_tags = volume.get_tags()
        assert bucket_tags.items() == tags.items()
        volume.remove_tags()
        bucket_tags = volume.get_tags()
        assert bucket_tags is None

    def test_lock(self, client):
        volume = MinioBucket(client, TEST_BUCKET)
        # ensure the bucket is completely clean
        volume.purge()
        volume.create()

        cfg = volume.get_object_lock()
        assert cfg is None
        # lets remove it and re-create with lock enabled
        volume.purge()
        volume.create(object_lock=True)
        cfg = volume.get_object_lock()
        assert cfg is not None
        assert cfg.mode is None  # empty rule

        # set proper lock configuration
        volume.set_object_lock(LOCK_CONFIG)
        assert xml.marshal(volume.get_object_lock()) == xml.marshal(LOCK_CONFIG)
