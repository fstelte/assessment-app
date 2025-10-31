import os
import sys
import boto3
from botocore.exceptions import BotoCoreError, ClientError

def upload(file_path, bucket, key_prefix=""):
    session = boto3.session.Session()
    s3 = session.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION')
    )
    key = f"{key_prefix.rstrip('/')}/{os.path.basename(file_path)}" if key_prefix else os.path.basename(file_path)
    try:
        s3.upload_file(file_path, bucket, key)
        print(f"s3_upload: uploaded {file_path} -> s3://{bucket}/{key}")
    except (BotoCoreError, ClientError) as e:
        print(f"s3_upload: ERROR uploading {file_path} -> s3://{bucket}/{key}: {e}", file=sys.stderr)
        raise

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: s3_upload.py <file> <bucket> [key_prefix]")
        sys.exit(2)
    upload(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
