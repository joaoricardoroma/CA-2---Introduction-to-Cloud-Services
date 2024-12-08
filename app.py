import boto3
import botocore.exceptions
from flask import Flask, render_template, request, redirect, url_for, flash
from s3_upload import create_bucket, s3
import re
import logging
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your_secret_key'

def is_valid_bucket_name(bucket_name):
    pattern = re.compile(r'^[a-z0-9]([a-z0-9\-\.]{1,61}[a-z0-9])?$')
    return pattern.match(bucket_name) is not None

@app.route('/')
def homepage():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'GET':
        response = s3.list_buckets()
        bucket_list = [bucket['Name'] for bucket in response['Buckets']]
        return render_template('S3_bucket/select_bucket.html', bucket_list=bucket_list)

@app.route('/create_bucket', methods=['GET', 'POST'])
def create_bucket_route():
    if request.method == 'POST':
        bucket_name = request.form['bucket_name']
        logger.info(f"Received request to create bucket: {bucket_name}")
        if is_valid_bucket_name(bucket_name):
            try:
                logger.info(f"Attempting to create bucket: {bucket_name}")
                create_bucket(bucket_name)
                logger.info(f"Bucket created successfully: {bucket_name}")

                # Get the list of buckets
                response = s3.list_buckets()
                bucket_list = [bucket['Name'] for bucket in response['Buckets']]

                return render_template('S3_bucket/select_bucket.html', bucket_list=bucket_list)
            except botocore.exceptions.ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'BucketAlreadyExists':
                    error_message = "The requested bucket name is not available. Please select a different name and try again."
                else:
                    error_message = f"Error creating bucket: {e}"
                flash(error_message)
                logger.error(f"Error creating bucket: {error_code} - {error_message}")
                return render_template('S3_bucket/create_bucket.html')
        else:
            error_message = "Invalid bucket name. Please follow the naming rules."
            flash(error_message)
            logger.error(f"Invalid bucket name: {bucket_name}")
            return render_template('S3_bucket/create_bucket.html')
    return render_template('S3_bucket/create_bucket.html')

@app.route('/bucket_created')
def bucket_created():
    bucket_name = request.args.get('bucket_name')
    bucket_url = request.args.get('bucket_url')
    return render_template('S3_bucket/bucket_created.html', bucket_name=bucket_name, bucket_url=bucket_url)

@app.route('/upload_to_bucket', methods=['GET', 'POST'])
def upload_to_bucket():
    if request.method == 'GET':
        bucket_name = request.args.get('bucket_name')
        if not bucket_name:
            flash("Bucket name is missing")
            return render_template('S3_bucket/select_bucket.html')
        return render_template('S3_bucket/upload_file.html', bucket_name=bucket_name)
    elif request.method == 'POST':
        bucket_name = request.form.get('bucket_name')
        if not bucket_name:
            flash("Bucket name is missing")
            return render_template('S3_bucket/select_bucket.html')

        file = request.files.get('file')
        if file and file.filename != '':
            s3.upload_fileobj(file, bucket_name, file.filename)
            flash(f"File '{file.filename}' uploaded successfully to bucket '{bucket_name}'")

            # Get the updated list of buckets
            response = s3.list_buckets()
            bucket_list = [bucket['Name'] for bucket in response['Buckets']]
            return render_template('S3_bucket/select_bucket.html', bucket_list=bucket_list)
        else:
            flash("No file selected or invalid file")
            return redirect(url_for('upload_to_bucket', bucket_name=bucket_name))

@app.route('/manage_bucket', methods=['GET'])
def manage_bucket():
    bucket_name = request.args.get('bucket_name')
    if not bucket_name:
        flash("Bucket name is missing")
        return redirect(url_for('upload_file'))

    try:
        response = s3.list_objects_v2(Bucket=bucket_name)
        objects = response.get('Contents', [])
        logger.info(f"Objects in bucket '{bucket_name}': {objects}")
        return render_template('S3_bucket/manage_bucket.html', bucket_name=bucket_name, objects=objects)
    except botocore.exceptions.ClientError as e:
        error_message = f"Error accessing bucket: {e}"
        flash(error_message)
        logger.error(error_message)
        return redirect(url_for('upload_file'))

# Create an EC2 client with credentials from environment variables
ec2_client = boto3.client(
    'ec2',
    region_name=os.getenv('AWS_REGION'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('AWS_SECRET_KEY')
)

@app.route('/list_instances')
def list_instances():
    try:
        response = ec2_client.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
        instances = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                asg_response = ec2_client.describe_tags(Filters=[
                    {'Name': 'resource-id', 'Values': [instance_id]},
                    {'Name': 'key', 'Values': ['aws:autoscaling:groupName']}
                ])
                asg_name = "any scaling group selected"
                if asg_response['Tags']:
                    asg_name = asg_response['Tags'][0]['Value']
                instances.append({
                    'InstanceId': instance_id,
                    'InstanceType': instance['InstanceType'],
                    'LaunchTime': instance['LaunchTime'],
                    'State': instance['State']['Name'],
                    'PublicIpAddress': instance.get('PublicIpAddress', 'N/A'),
                    'AutoScalingGroup': asg_name
                })
        return render_template('EC2/list_instances.html', instances=instances)
    except botocore.exceptions.ClientError as e:
        error_message = f"Error retrieving instances: {e}"
        flash(error_message)
        logger.error(error_message)
        return redirect(url_for('homepage'))


asg_client = boto3.client(
    'autoscaling',
    region_name=os.getenv('AWS_REGION'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('AWS_SECRET_KEY')
)
@app.route('/list_auto_scaling_groups')
def list_auto_scaling_groups():
    try:
        response = asg_client.describe_auto_scaling_groups()
        auto_scaling_groups = []
        for asg in response['AutoScalingGroups']:
            instances = [instance['InstanceId'] for instance in asg['Instances']]
            auto_scaling_groups.append({
                'AutoScalingGroupName': asg['AutoScalingGroupName'],
                'Instances': instances
            })
        return render_template('EC2/list_auto_scaling_groups.html', auto_scaling_groups=auto_scaling_groups)
    except botocore.exceptions.ClientError as e:
        error_message = f"Error retrieving auto scaling groups: {e}"
        flash(error_message)
        logger.error(error_message)
        return redirect(url_for('homepage'))
    except botocore.exceptions.NoCredentialsError:
        error_message = "AWS credentials not found. Please configure your credentials."
        flash(error_message)
        logger.error(error_message)
        return redirect(url_for('homepage'))


if __name__ == '__main__':
    app.run(debug=True)