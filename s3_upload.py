import json
import boto3
import os
from dotenv import load_dotenv
import re

# Load environment variables from .env file
load_dotenv()

# AWS credentials from the .env file
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
AWS_REGION = os.getenv("AWS_REGION")

# S3 Client
s3 = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

def is_valid_bucket_name(bucket_name):
    """
    Validate the bucket name according to AWS S3 bucket naming rules.
    """
    pattern = re.compile(r'^[a-z0-9.-]{3,63}$')
    if not pattern.match(bucket_name):
        return False
    if '..' in bucket_name or '.-' in bucket_name or '-.' in bucket_name or '--' in bucket_name:
        return False
    if bucket_name.startswith('.') or bucket_name.startswith('-') or bucket_name.endswith('.') or bucket_name.endswith('-'):
        return False
    return True

def create_bucket(bucket_name):
    if not is_valid_bucket_name(bucket_name):
        raise ValueError("Invalid bucket name. Please follow the naming rules.")

    s3.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={
            'LocationConstraint': AWS_REGION
        }
    )

    # Disable BlockPublicPolicy for the bucket
    s3.put_public_access_block(
        Bucket=bucket_name,
        PublicAccessBlockConfiguration={
            'BlockPublicAcls': False,
            'IgnorePublicAcls': False,
            'BlockPublicPolicy': False,
            'RestrictPublicBuckets': False
        }
    )

    # Set the bucket policy to allow public read access
    bucket_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/*"
            }
        ]
    }

    # Convert the policy to a JSON string
    bucket_policy = json.dumps(bucket_policy)

    # Set the new policy on the given bucket
    s3.put_bucket_policy(Bucket=bucket_name, Policy=bucket_policy)
