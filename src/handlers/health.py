"""
Health Check Handler

Simple health check endpoint for monitoring.
"""

import json
from datetime import datetime


def handler(event, context):
    """
    Health check endpoint.
    
    Returns service status and version information.
    """
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'status': 'healthy',
            'service': 'loan-eligibility-engine',
            'version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat()
        })
    }
