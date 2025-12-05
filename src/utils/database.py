"""
Database utility functions
"""

import os
import psycopg2
from contextlib import contextmanager


def get_db_config():
    """Get database configuration from environment variables."""
    return {
        'host': os.environ.get('DB_HOST'),
        'port': int(os.environ.get('DB_PORT', 5432)),
        'database': os.environ.get('DB_NAME', 'loan_eligibility'),
        'user': os.environ.get('DB_USER'),
        'password': os.environ.get('DB_PASSWORD'),
        'connect_timeout': 10
    }


@contextmanager
def get_db_connection():
    """
    Context manager for database connections.
    
    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
    """
    conn = None
    try:
        conn = psycopg2.connect(**get_db_config())
        yield conn
    finally:
        if conn:
            conn.close()


def execute_query(query, params=None, fetch=True):
    """
    Execute a database query.
    
    Args:
        query: SQL query string
        params: Query parameters (tuple or dict)
        fetch: Whether to fetch results
        
    Returns:
        Query results if fetch=True, else None
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            if fetch:
                return cursor.fetchall()
            conn.commit()
            return None
        finally:
            cursor.close()


def execute_many(query, params_list):
    """
    Execute a query with multiple parameter sets.
    
    Args:
        query: SQL query string
        params_list: List of parameter tuples
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.executemany(query, params_list)
            conn.commit()
        finally:
            cursor.close()
