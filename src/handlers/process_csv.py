"""
Process CSV Handler - S3 Event Triggered

This Lambda function is triggered when a CSV file is uploaded to S3.
It parses the CSV data and stores it in PostgreSQL database,
then triggers the n8n matching workflow via webhook.
"""

import csv
import io
import json
import os
from datetime import datetime
from urllib.parse import unquote_plus

import boto3
import psycopg2
import requests
from psycopg2.extras import execute_batch


def handler(event, context):
    """
    Process CSV file uploaded to S3.
    
    1. Read CSV file from S3
    2. Parse and validate user data
    3. Store in PostgreSQL database
    4. Trigger n8n webhook for matching workflow
    """
    print(f"Event received: {json.dumps(event)}")
    
    try:
        # Get S3 object info from event
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        
        print(f"Processing file: s3://{bucket}/{key}")
        
        # Download file from S3
        s3_client = boto3.client('s3')
        response = s3_client.get_object(Bucket=bucket, Key=key)
        csv_content = response['Body'].read().decode('utf-8')
        
        # Parse CSV
        users = parse_csv(csv_content)
        print(f"Parsed {len(users)} users from CSV")
        
        if not users:
            print("No valid users found in CSV")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No valid users found in CSV'})
            }
        
        # Store in database
        batch_id = store_users(users)
        print(f"Stored users with batch_id: {batch_id}")
        
        # Trigger n8n webhook
        webhook_response = trigger_n8n_webhook(batch_id, len(users))
        print(f"n8n webhook response: {webhook_response}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'message': f'Processed {len(users)} users',
                'batchId': batch_id
            })
        }
        
    except Exception as e:
        print(f"Error processing CSV: {str(e)}")
        raise e


def parse_csv(csv_content):
    """
    Parse CSV content and validate user data.
    
    Expected columns: user_id, email, monthly_income, credit_score, employment_status, age
    """
    users = []
    reader = csv.DictReader(io.StringIO(csv_content))
    
    # Normalize header names (handle case variations and extra spaces)
    required_fields = ['user_id', 'email', 'monthly_income', 'credit_score', 'employment_status', 'age']
    
    for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
        try:
            # Normalize keys (lowercase, strip spaces)
            normalized_row = {k.lower().strip(): v.strip() for k, v in row.items()}
            
            # Validate and extract fields
            user = {
                'user_id': normalized_row.get('user_id', ''),
                'email': normalized_row.get('email', ''),
                'monthly_income': float(normalized_row.get('monthly_income', 0)),
                'credit_score': int(normalized_row.get('credit_score', 0)),
                'employment_status': normalized_row.get('employment_status', '').lower(),
                'age': int(normalized_row.get('age', 0))
            }
            
            # Basic validation
            if not user['user_id'] or not user['email']:
                print(f"Row {row_num}: Missing user_id or email, skipping")
                continue
            
            if user['monthly_income'] < 0:
                print(f"Row {row_num}: Invalid monthly_income, skipping")
                continue
            
            if user['credit_score'] < 300 or user['credit_score'] > 900:
                print(f"Row {row_num}: Invalid credit_score (should be 300-900), skipping")
                continue
            
            if user['age'] < 18 or user['age'] > 100:
                print(f"Row {row_num}: Invalid age, skipping")
                continue
            
            users.append(user)
            
        except (ValueError, KeyError) as e:
            print(f"Row {row_num}: Error parsing row - {str(e)}, skipping")
            continue
    
    return users


def store_users(users):
    """
    Store users in PostgreSQL database.
    
    Returns the batch_id for this upload.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Generate batch ID
        batch_id = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        
        # Ensure table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) UNIQUE NOT NULL,
                email VARCHAR(255) NOT NULL,
                monthly_income DECIMAL(12, 2) NOT NULL,
                credit_score INTEGER NOT NULL,
                employment_status VARCHAR(50) NOT NULL,
                age INTEGER NOT NULL,
                batch_id VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed BOOLEAN DEFAULT FALSE
            );
            
            CREATE INDEX IF NOT EXISTS idx_users_batch_id ON users(batch_id);
            CREATE INDEX IF NOT EXISTS idx_users_credit_score ON users(credit_score);
            CREATE INDEX IF NOT EXISTS idx_users_monthly_income ON users(monthly_income);
            CREATE INDEX IF NOT EXISTS idx_users_processed ON users(processed);
        """)
        
        # Insert users (upsert on conflict)
        insert_query = """
            INSERT INTO users (user_id, email, monthly_income, credit_score, employment_status, age, batch_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                email = EXCLUDED.email,
                monthly_income = EXCLUDED.monthly_income,
                credit_score = EXCLUDED.credit_score,
                employment_status = EXCLUDED.employment_status,
                age = EXCLUDED.age,
                batch_id = EXCLUDED.batch_id,
                processed = FALSE
        """
        
        user_data = [
            (u['user_id'], u['email'], u['monthly_income'], u['credit_score'], 
             u['employment_status'], u['age'], batch_id)
            for u in users
        ]
        
        execute_batch(cursor, insert_query, user_data, page_size=100)
        conn.commit()
        
        return batch_id
        
    finally:
        cursor.close()
        conn.close()


def trigger_n8n_webhook(batch_id, user_count):
    """
    Trigger n8n matching workflow via webhook.
    """
    webhook_url = os.environ.get('N8N_WEBHOOK_URL')
    
    if not webhook_url:
        print("N8N_WEBHOOK_URL not configured, skipping webhook trigger")
        return {'skipped': True, 'reason': 'Webhook URL not configured'}
    
    try:
        response = requests.post(
            f"{webhook_url}/webhook/matching-trigger",
            json={
                'batchId': batch_id,
                'userCount': user_count,
                'timestamp': datetime.utcnow().isoformat()
            },
            timeout=30
        )
        
        return {
            'status_code': response.status_code,
            'response': response.text
        }
        
    except requests.RequestException as e:
        print(f"Failed to trigger n8n webhook: {str(e)}")
        return {'error': str(e)}


def get_db_connection():
    """
    Create PostgreSQL database connection.
    """
    return psycopg2.connect(
        host=os.environ.get('DB_HOST'),
        port=os.environ.get('DB_PORT', 5432),
        database=os.environ.get('DB_NAME'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        connect_timeout=10
    )
