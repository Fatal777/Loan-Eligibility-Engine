"""
Local Flask API for testing the Loan Eligibility Engine
without deploying to AWS Lambda.

Run with: python local_api.py
API will be available at http://localhost:3000
"""

import os
import sys
import json
import uuid
import pandas as pd
from io import StringIO
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.database import get_db_connection, execute_query
from utils.validation import validate_user_data

load_dotenv()

app = Flask(__name__)
CORS(app)

# =====================================================
# HEALTH CHECK ENDPOINT
# =====================================================
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return jsonify({
        "status": "healthy",
        "service": "loan-eligibility-engine-local",
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    })


# =====================================================
# CSV UPLOAD ENDPOINT (Direct upload, no S3)
# =====================================================
@app.route('/upload-csv', methods=['POST'])
def upload_csv():
    """
    Direct CSV upload endpoint for local testing.
    Accepts CSV file or JSON with CSV content.
    """
    batch_id = f"BATCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    try:
        # Handle file upload
        if 'file' in request.files:
            file = request.files['file']
            csv_content = file.read().decode('utf-8')
        # Handle JSON with CSV content
        elif request.is_json:
            data = request.get_json()
            csv_content = data.get('csv_content', '')
        # Handle form data
        else:
            csv_content = request.form.get('csv_content', '')
        
        if not csv_content:
            return jsonify({"error": "No CSV content provided"}), 400
        
        # Parse CSV
        df = pd.read_csv(StringIO(csv_content))
        required_columns = ['user_id', 'email', 'monthly_income', 'credit_score', 'employment_status', 'age']
        
        # Normalize column names (lowercase, strip whitespace)
        df.columns = [col.lower().strip() for col in df.columns]
        
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            return jsonify({"error": f"Missing columns: {missing_cols}"}), 400
        
        # Process and store users
        users_added = 0
        users_failed = 0
        errors = []
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            for idx, row in df.iterrows():
                user_data = row.to_dict()
                is_valid, validation_errors = validate_user_data(user_data)
                
                if not is_valid:
                    users_failed += 1
                    errors.append(f"Row {idx + 2}: {', '.join(validation_errors)}")
                    continue
                
                try:
                    # Get name if present
                    name = str(user_data.get('name', '')) if 'name' in user_data else None
                    
                    cursor.execute("""
                        INSERT INTO users (user_id, name, email, monthly_income, credit_score, 
                                          employment_status, age, batch_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (user_id) DO UPDATE SET
                            name = EXCLUDED.name,
                            email = EXCLUDED.email,
                            monthly_income = EXCLUDED.monthly_income,
                            credit_score = EXCLUDED.credit_score,
                            employment_status = EXCLUDED.employment_status,
                            age = EXCLUDED.age,
                            batch_id = EXCLUDED.batch_id,
                            updated_at = CURRENT_TIMESTAMP
                    """, (
                        str(user_data['user_id']),
                        name,
                        str(user_data['email']),
                        float(user_data['monthly_income']),
                        int(user_data['credit_score']),
                        str(user_data['employment_status']).lower(),
                        int(user_data['age']),
                        batch_id
                    ))
                    users_added += 1
                except Exception as e:
                    users_failed += 1
                    errors.append(f"Row {idx + 1}: {str(e)}")
            
            conn.commit()
        
        return jsonify({
            "success": True,
            "batch_id": batch_id,
            "users_added": users_added,
            "users_failed": users_failed,
            "errors": errors[:10]  # Limit errors shown
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =====================================================
# TRIGGER MATCHING ENDPOINT
# =====================================================
@app.route('/trigger-matching', methods=['POST'])
def trigger_matching():
    """
    Trigger the matching process for a batch of users.
    This implements the 4-stage matching optimization.
    """
    try:
        # Handle both JSON and empty body requests
        data = {}
        if request.is_json:
            data = request.get_json(silent=True) or {}
        batch_id = data.get('batch_id')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get users to process
            if batch_id:
                cursor.execute("""
                    SELECT user_id, email, monthly_income, credit_score, 
                           employment_status, age 
                    FROM users 
                    WHERE batch_id = %s AND processed = false
                """, (batch_id,))
            else:
                cursor.execute("""
                    SELECT user_id, email, monthly_income, credit_score, 
                           employment_status, age 
                    FROM users 
                    WHERE processed = false
                    LIMIT 100
                """)
            
            users = cursor.fetchall()
            
            if not users:
                return jsonify({
                    "message": "No unprocessed users found",
                    "matches_created": 0
                })
            
            # Get active loan products
            cursor.execute("""
                SELECT product_id, product_name, provider_name,
                       min_monthly_income, min_credit_score, max_credit_score,
                       required_employment_status, min_age, max_age
                FROM loan_products
                WHERE is_active = true
            """)
            products = cursor.fetchall()
            
            matches_created = 0
            match_batch_id = f"MATCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Process each user
            for user in users:
                user_id, email, income, credit_score, emp_status, age = user
                
                # Stage 1: Filter by credit score (fastest check)
                eligible_products = [p for p in products 
                                   if p[4] <= credit_score <= p[5]]  # min/max credit score
                
                # Stage 2: Filter by income
                eligible_products = [p for p in eligible_products 
                                   if p[3] <= income]  # min_monthly_income
                
                # Stage 3: Filter by age
                eligible_products = [p for p in eligible_products 
                                   if p[7] <= age <= p[8]]  # min_age, max_age
                
                # Stage 4: Filter by employment status
                final_matches = []
                for p in eligible_products:
                    required_status = p[6]  # required_employment_status
                    if required_status:
                        statuses = [s.strip().lower() for s in required_status.split(',')]
                        if emp_status.lower() in statuses:
                            final_matches.append(p)
                    else:
                        final_matches.append(p)
                
                # Calculate match scores and store
                for product in final_matches:
                    product_id = product[0]
                    
                    # Simple scoring algorithm
                    score = 60  # Base score
                    if credit_score >= 750:
                        score += 20
                    elif credit_score >= 700:
                        score += 10
                    if income >= 50000:
                        score += 10
                    if emp_status == 'salaried':
                        score += 10
                    
                    cursor.execute("""
                        INSERT INTO matches (user_id, product_id, match_score, 
                                           match_reason, match_type, batch_id)
                        VALUES (%s, %s, %s, %s, 'auto', %s)
                        ON CONFLICT (user_id, product_id, batch_id) DO NOTHING
                    """, (
                        user_id,
                        product_id,
                        min(score, 100),
                        f"Matched based on eligibility criteria (CS: {credit_score}, Income: ₹{income:,.0f})",
                        match_batch_id
                    ))
                    matches_created += 1
                
                # Mark user as processed
                cursor.execute("""
                    UPDATE users SET processed = true 
                    WHERE user_id = %s
                """, (user_id,))
            
            conn.commit()
            
        return jsonify({
            "success": True,
            "users_processed": len(users),
            "matches_created": matches_created,
            "match_batch_id": match_batch_id
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =====================================================
# GET MATCHES ENDPOINT
# =====================================================
@app.route('/matches', methods=['GET'])
def get_matches():
    """Get all matches or filter by batch/user"""
    try:
        batch_id = request.args.get('batch_id')
        user_id = request.args.get('user_id')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT m.match_id, m.user_id, u.email, 
                       m.product_id, p.product_name, p.provider_name,
                       m.match_score, m.match_reason, m.created_at
                FROM matches m
                JOIN users u ON m.user_id = u.user_id
                JOIN loan_products p ON m.product_id = p.product_id
            """
            params = []
            
            if batch_id:
                query += " WHERE m.batch_id = %s"
                params.append(batch_id)
            elif user_id:
                query += " WHERE m.user_id = %s"
                params.append(user_id)
            
            query += " ORDER BY m.match_score DESC LIMIT 100"
            
            cursor.execute(query, params if params else None)
            rows = cursor.fetchall()
            
            matches = []
            for row in rows:
                matches.append({
                    "match_id": str(row[0]),
                    "user_id": row[1],
                    "email": row[2],
                    "product_id": row[3],
                    "product_name": row[4],
                    "provider_name": row[5],
                    "match_score": float(row[6]) if row[6] else None,
                    "match_reason": row[7],
                    "created_at": row[8].isoformat() if row[8] else None
                })
            
            return jsonify({
                "count": len(matches),
                "matches": matches
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =====================================================
# GET LOAN PRODUCTS ENDPOINT
# =====================================================
@app.route('/products', methods=['GET'])
def get_products():
    """Get all loan products"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT product_id, product_name, provider_name,
                       interest_rate_min, interest_rate_max,
                       min_loan_amount, max_loan_amount,
                       min_monthly_income, min_credit_score, max_credit_score,
                       required_employment_status, min_age, max_age,
                       is_active
                FROM loan_products
                ORDER BY provider_name
            """)
            rows = cursor.fetchall()
            
            products = []
            for row in rows:
                products.append({
                    "product_id": row[0],
                    "product_name": row[1],
                    "provider_name": row[2],
                    "interest_rate_min": float(row[3]) if row[3] else None,
                    "interest_rate_max": float(row[4]) if row[4] else None,
                    "min_loan_amount": float(row[5]) if row[5] else None,
                    "max_loan_amount": float(row[6]) if row[6] else None,
                    "min_monthly_income": float(row[7]) if row[7] else None,
                    "min_credit_score": row[8],
                    "max_credit_score": row[9],
                    "required_employment_status": row[10],
                    "min_age": row[11],
                    "max_age": row[12],
                    "is_active": row[13]
                })
            
            return jsonify({
                "count": len(products),
                "products": products
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =====================================================
# GET USERS ENDPOINT
# =====================================================
@app.route('/users', methods=['GET'])
def get_users():
    """Get all users"""
    try:
        batch_id = request.args.get('batch_id')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            if batch_id:
                cursor.execute("""
                    SELECT user_id, email, monthly_income, credit_score,
                           employment_status, age, batch_id, processed, created_at
                    FROM users
                    WHERE batch_id = %s
                    ORDER BY created_at DESC
                """, (batch_id,))
            else:
                cursor.execute("""
                    SELECT user_id, email, monthly_income, credit_score,
                           employment_status, age, batch_id, processed, created_at
                    FROM users
                    ORDER BY created_at DESC
                    LIMIT 100
                """)
            
            rows = cursor.fetchall()
            
            users = []
            for row in rows:
                users.append({
                    "user_id": row[0],
                    "email": row[1],
                    "monthly_income": float(row[2]),
                    "credit_score": row[3],
                    "employment_status": row[4],
                    "age": row[5],
                    "batch_id": row[6],
                    "processed": row[7],
                    "created_at": row[8].isoformat() if row[8] else None
                })
            
            return jsonify({
                "count": len(users),
                "users": users
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =====================================================
# MAIN
# =====================================================
if __name__ == '__main__':
    print("=" * 60)
    print("LOAN ELIGIBILITY ENGINE - LOCAL API")
    print("=" * 60)
    print(f"API running at: http://localhost:3000")
    print("")
    print("Endpoints:")
    print("  GET  /health         - Health check")
    print("  POST /upload-csv     - Upload CSV file")
    print("  POST /trigger-matching - Run matching algorithm")
    print("  GET  /matches        - Get matches (optional: ?batch_id=X)")
    print("  GET  /products       - Get loan products")
    print("  GET  /users          - Get users (optional: ?batch_id=X)")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=3000, debug=True)
