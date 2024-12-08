from flask import Flask, render_template, request, redirect, url_for, flash
from s3_upload import create_bucket, s3
import re
import logging
import botocore.exceptions

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
            return render_template('S3_bucket/select_bucket.html')
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

if __name__ == '__main__':
    app.run(debug=True)