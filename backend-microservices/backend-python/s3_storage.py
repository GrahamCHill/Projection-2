import os
import boto3
from botocore.client import Config
from datetime import datetime
import hashlib

# MinIO configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "diagrams")

# Initialize S3 client for MinIO
s3_client = boto3.client(
    's3',
    endpoint_url=f'http://{MINIO_ENDPOINT}',
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    config=Config(signature_version='s3v4'),
    region_name='us-east-1'
)

def ensure_bucket_exists():
    """Create bucket if it doesn't exist"""
    try:
        s3_client.head_bucket(Bucket=MINIO_BUCKET)
    except:
        s3_client.create_bucket(Bucket=MINIO_BUCKET)
        print(f"Created bucket: {MINIO_BUCKET}")

def generate_s3_key(content: str, prefix: str = "diagrams") -> str:
    """Generate unique S3 key based on content hash and timestamp"""
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:12]
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}/{timestamp}_{content_hash}.mmd"

def upload_diagram(content: str, s3_key: str = None) -> str:
    """Upload diagram content to MinIO, returns S3 key"""
    ensure_bucket_exists()
    
    if not s3_key:
        s3_key = generate_s3_key(content)
    
    s3_client.put_object(
        Bucket=MINIO_BUCKET,
        Key=s3_key,
        Body=content.encode('utf-8'),
        ContentType='text/plain'
    )
    
    return s3_key

def download_diagram(s3_key: str) -> str:
    """Download diagram content from MinIO"""
    response = s3_client.get_object(Bucket=MINIO_BUCKET, Key=s3_key)
    return response['Body'].read().decode('utf-8')

def delete_diagram(s3_key: str):
    """Delete diagram from MinIO"""
    s3_client.delete_object(Bucket=MINIO_BUCKET, Key=s3_key)

def get_presigned_url(s3_key: str, expiration: int = 3600) -> str:
    """Generate presigned URL for diagram access"""
    return s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': MINIO_BUCKET, 'Key': s3_key},
        ExpiresIn=expiration
    )
