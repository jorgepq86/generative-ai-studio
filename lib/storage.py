import uuid


def get_client(region_name, aws_access_key_id=None, aws_secret_access_key=None):
    import boto3
    return boto3.client(
        "s3",
        region_name=region_name,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )


def save_image(client, bucket, user, image_bytes):
    key = f"images/{user}/{uuid.uuid4()}.png"
    client.put_object(
        Bucket=bucket, Key=key, Body=image_bytes, ContentType="image/png", ServerSideEncryption="AES256"
    )
    return key


def get_image_url(client, bucket, s3_key, expires_in=3600):
    return client.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": s3_key}, ExpiresIn=expires_in
    )
