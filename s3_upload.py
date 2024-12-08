import boto3
import os
from dotenv import load_dotenv

# Load environment variables
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

def create_bucket(bucket_name):
    """Create an S3 bucket"""
    try:
        response = s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': AWS_REGION}
        )
        print(f"Bucket {bucket_name} created successfully.")
        return response
    except Exception as e:
        print(f"Error creating bucket: {e}")

def upload_file(bucket_name, file_name, file_path):
    """Upload a file to the S3 bucket"""
    try:
        s3.upload_file(file_path, bucket_name, file_name)
        print(f"File {file_name} uploaded to bucket {bucket_name}.")
    except Exception as e:
        print(f"Error uploading file: {e}")

def list_bucket_items(bucket_name):
    """List items in an S3 bucket"""
    try:
        response = s3.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in response:
            for obj in response['Contents']:
                print(f"Item: {obj['Key']}")
        else:
            print("Bucket is empty.")
    except Exception as e:
        print(f"Error listing bucket items: {e}")


bucket_name = "digitech-web-assets-2023158"
create_bucket(bucket_name)
upload_file(bucket_name, "image.jpg", "path/to/image.jpg")  # Replace with your image path
list_bucket_items(bucket_name)