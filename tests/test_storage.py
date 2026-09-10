import boto3
from moto import mock_aws

from lib import storage


@mock_aws
def test_save_image_uploads_to_s3_and_returns_key():
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket="test-bucket")

    key = storage.save_image(client, "test-bucket", "redactor", b"fake-png-bytes")

    assert key.startswith("images/redactor/")
    assert key.endswith(".png")
    obj = client.get_object(Bucket="test-bucket", Key=key)
    assert obj["Body"].read() == b"fake-png-bytes"


@mock_aws
def test_save_image_sets_server_side_encryption():
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket="test-bucket")

    key = storage.save_image(client, "test-bucket", "redactor", b"data")

    head = client.head_object(Bucket="test-bucket", Key=key)
    assert head["ServerSideEncryption"] == "AES256"


@mock_aws
def test_get_image_url_returns_url_containing_bucket_and_key():
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket="test-bucket")
    key = storage.save_image(client, "test-bucket", "redactor", b"data")

    url = storage.get_image_url(client, "test-bucket", key)

    assert "test-bucket" in url
    assert key in url
