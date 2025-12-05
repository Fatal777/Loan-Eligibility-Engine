"""
Trigger Matching Handler - Manual Trigger for n8n Workflow

This endpoint allows manual triggering of the matching workflow,
useful for testing and debugging.
"""

import json
import os
from datetime import datetime

import psycopg2
import requests


def handler(event, context):
    """
    Manually trigger the n8n matching workflow.
    
    Request Body (optional):
        - batchId: Specific batch to process (default: latest)
    """
    try:
        # Parse request body
        body = {}
        if event.get('body'):
            body = json.loads(event['body'])
        
        batch_id = body.get('batchId')
        
        # If no batch_id provided, get the latest one
        if not batch_id:
            batch_id = get_latest_batch_id()
            if not batch_id:
                return _response(404, {'error': 'No user batches found'})
        
        # Get user count for this batch
        user_count = get_batch_user_count(batch_id)
        
        # Trigger n8n webhook
        webhook_url = os.environ.get('N8N_WEBHOOK_URL')
        if not webhook_url:
            return _response(500, {'error': 'N8N_WEBHOOK_URL not configured'})
        
        response = requests.post(
            f"{webhook_url}/webhook/matching-trigger",
            json={
                'batchId': batch_id,
                'userCount': user_count,
                'timestamp': datetime.utcnow().isoformat(),
                'manualTrigger': True
            },
            timeout=30
        )
        
        return _response(200, {
            'success': True,
            'message': 'Matching workflow triggered',
            'batchId': batch_id,
            'userCount': user_count,
            'n8nResponse': {
                'statusCode': response.status_code,
                'body': response.text
            }
        })
        
    except requests.RequestException as e:
        return _response(500, {'error': f'Failed to trigger n8n: {str(e)}'})
    except Exception as e:
        print(f"Error: {str(e)}")
        return _response(500, {'error': str(e)})


def get_latest_batch_id():
    """Get the most recent batch ID from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT batch_id FROM users 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        cursor.close()
        conn.close()


def get_batch_user_count(batch_id):
    """Get the number of users in a batch."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT COUNT(*) FROM users WHERE batch_id = %s",
            (batch_id,)
        )
        result = cursor.fetchone()
        return result[0] if result else 0
    finally:
        cursor.close()
        conn.close()


def get_db_connection():
    """Create PostgreSQL database connection."""
    return psycopg2.connect(
        host=os.environ.get('DB_HOST'),
        port=os.environ.get('DB_PORT', 5432),
        database=os.environ.get('DB_NAME'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        connect_timeout=10
    )


def _response(status_code, body):
    """Generate API response with CORS headers."""
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Content-Type': 'application/json'
        },
        'body': json.dumps(body)
    }
