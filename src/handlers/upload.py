"""
Upload Handler - Generate Presigned URLs for S3 Upload

This implements an event-driven pattern for CSV uploads:
1. Frontend requests a presigned URL
2. Frontend uploads directly to S3 using the presigned URL
3. S3 triggers the processCSV Lambda function

This approach avoids Lambda timeout and payload size limits.
"""

import json
import os
import uuid
from datetime import datetime

import boto3
from botocore.exceptions import ClientError


def get_presigned_url(event, context):
    """
    Generate a presigned URL for uploading CSV files to S3.
    
    Query Parameters:
        - filename: Original filename (optional, for metadata)
    
    Returns:
        - presignedUrl: URL for PUT request
        - uploadId: Unique identifier for this upload
        - key: S3 object key
    """
    try:
        # Get query parameters
        query_params = event.get('queryStringParameters') or {}
        original_filename = query_params.get('filename', 'users.csv')
        
        # Generate unique upload ID and S3 key
        upload_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        s3_key = f"uploads/{timestamp}_{upload_id}.csv"
        
        # Get bucket name from environment
        bucket_name = os.environ.get('S3_BUCKET')
        if not bucket_name:
            return _error_response(500, "S3 bucket not configured")
        
        # Create S3 client
        s3_client = boto3.client('s3')
        
        # Generate presigned URL for PUT operation
        # Note: Removed metadata to simplify client-side upload
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket_name,
                'Key': s3_key,
                'ContentType': 'text/csv'
            },
            ExpiresIn=3600  # URL expires in 1 hour
        )
        
        return {
            'statusCode': 200,
            'headers': _cors_headers(),
            'body': json.dumps({
                'success': True,
                'presignedUrl': presigned_url,
                'uploadId': upload_id,
                'key': s3_key,
                'bucket': bucket_name,
                'expiresIn': 3600,
                'message': 'Use PUT request with Content-Type: text/csv to upload'
            })
        }
        
    except ClientError as e:
        print(f"AWS Error: {str(e)}")
        return _error_response(500, f"Failed to generate presigned URL: {str(e)}")
    except Exception as e:
        print(f"Error: {str(e)}")
        return _error_response(500, f"Internal server error: {str(e)}")


def _cors_headers():
    """Return CORS headers for API responses."""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,OPTIONS',
        'Content-Type': 'application/json'
    }


def _error_response(status_code, message):
    """Generate an error response."""
    return {
        'statusCode': status_code,
        'headers': _cors_headers(),
        'body': json.dumps({
            'success': False,
            'error': message
        })
    }
