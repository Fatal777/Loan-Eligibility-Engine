"""
Test script to verify database connection and handlers
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("LOAN ELIGIBILITY ENGINE - LOCAL TEST")
print("=" * 60)

# Test 1: Database Connection
print("\n[1] Testing Database Connection...")
try:
    from utils.database import get_db_connection, execute_query
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"   ✅ Connected to PostgreSQL: {version[:50]}...")
        
        # Check tables
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cursor.fetchall()]
        print(f"   ✅ Tables found: {', '.join(tables)}")
        
        # Check sample loan products
        cursor.execute("SELECT COUNT(*) FROM loan_products;")
        count = cursor.fetchone()[0]
        print(f"   ✅ Loan products in database: {count}")
        
except Exception as e:
    print(f"   ❌ Database connection failed: {e}")
    sys.exit(1)

# Test 2: Import handlers
print("\n[2] Testing Handler Imports...")
try:
    from handlers import upload, process_csv, trigger_matching, health
    print("   ✅ All handlers imported successfully")
except Exception as e:
    print(f"   ❌ Handler import failed: {e}")

# Test 3: Health check endpoint
print("\n[3] Testing Health Check Handler...")
try:
    result = health.handler({}, {})
    print(f"   ✅ Health check: {result['statusCode']} - {result['body'][:50]}...")
except Exception as e:
    print(f"   ❌ Health check failed: {e}")

# Test 4: Query loan products
print("\n[4] Fetching Loan Products...")
try:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT product_id, product_name, provider_name, 
                   min_credit_score, min_monthly_income
            FROM loan_products
            ORDER BY provider_name;
        """)
        products = cursor.fetchall()
        
        print("   Available Loan Products:")
        print("   " + "-" * 80)
        for p in products:
            print(f"   {p[0]:15} | {p[1]:30} | {p[2]:20} | CS: {p[3]} | Inc: ₹{p[4]:,.0f}")
        print("   " + "-" * 80)
        print(f"   ✅ Total: {len(products)} products")
except Exception as e:
    print(f"   ❌ Query failed: {e}")

# Test 5: Simulate CSV processing
print("\n[5] Testing CSV Processing Logic...")
try:
    import pandas as pd
    import io
    
    # Sample CSV data
    sample_csv = """user_id,email,monthly_income,credit_score,employment_status,age
U001,john@example.com,50000,750,salaried,28
U002,jane@example.com,35000,680,salaried,32
U003,bob@example.com,80000,800,self-employed,45
U004,alice@example.com,25000,620,salaried,25
U005,charlie@example.com,100000,850,self-employed,38
"""
    
    df = pd.read_csv(io.StringIO(sample_csv))
    print(f"   ✅ Parsed sample CSV: {len(df)} users")
    print(f"   Columns: {list(df.columns)}")
    
    # Validate data
    from utils.validation import validate_user_data
    valid_count = 0
    for _, row in df.iterrows():
        is_valid, _ = validate_user_data(row.to_dict())
        if is_valid:
            valid_count += 1
    print(f"   ✅ Validation passed: {valid_count}/{len(df)} users valid")
    
except Exception as e:
    print(f"   ❌ CSV processing test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 6: Test matching logic
print("\n[6] Testing Matching Logic...")
try:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Find eligible products for a sample user
        test_user = {
            'credit_score': 750,
            'monthly_income': 50000,
            'employment_status': 'salaried',
            'age': 28
        }
        
        cursor.execute("""
            SELECT product_id, product_name, provider_name
            FROM loan_products
            WHERE is_active = true
              AND min_credit_score <= %s
              AND max_credit_score >= %s
              AND min_monthly_income <= %s
              AND min_age <= %s
              AND max_age >= %s
              AND (required_employment_status LIKE '%%' || %s || '%%' 
                   OR required_employment_status IS NULL)
        """, (
            test_user['credit_score'],
            test_user['credit_score'],
            test_user['monthly_income'],
            test_user['age'],
            test_user['age'],
            test_user['employment_status']
        ))
        
        matches = cursor.fetchall()
        print(f"   Test user: Credit Score={test_user['credit_score']}, Income=₹{test_user['monthly_income']:,}, Status={test_user['employment_status']}")
        print(f"   ✅ Eligible for {len(matches)} loan products:")
        for m in matches:
            print(f"      - {m[1]} ({m[2]})")
            
except Exception as e:
    print(f"   ❌ Matching test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("All local tests completed!")
print("=" * 60)
print("\nNext Steps:")
print("  1. Access n8n at http://localhost:5678 (admin/admin123)")
print("  2. Import workflows from n8n/workflows/ folder")
print("  3. Set up ngrok for external webhook access")
print("  4. Configure Gemini API key in .env")
print("=" * 60)
