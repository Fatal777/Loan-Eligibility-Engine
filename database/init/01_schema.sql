-- =====================================================
-- LOAN ELIGIBILITY ENGINE - DATABASE SCHEMA
-- =====================================================
-- This script initializes the PostgreSQL database
-- with all required tables and indexes.
-- =====================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- USERS TABLE
-- Stores user data uploaded via CSV
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    monthly_income DECIMAL(12, 2) NOT NULL,
    credit_score INTEGER NOT NULL CHECK (credit_score >= 300 AND credit_score <= 900),
    employment_status VARCHAR(50) NOT NULL,
    age INTEGER NOT NULL CHECK (age >= 18 AND age <= 100),
    batch_id VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE
);

-- Indexes for users table
CREATE INDEX IF NOT EXISTS idx_users_batch_id ON users(batch_id);
CREATE INDEX IF NOT EXISTS idx_users_credit_score ON users(credit_score);
CREATE INDEX IF NOT EXISTS idx_users_monthly_income ON users(monthly_income);
CREATE INDEX IF NOT EXISTS idx_users_employment_status ON users(employment_status);
CREATE INDEX IF NOT EXISTS idx_users_processed ON users(processed);
CREATE INDEX IF NOT EXISTS idx_users_age ON users(age);

-- =====================================================
-- LOAN PRODUCTS TABLE
-- Stores loan products crawled from financial websites
-- =====================================================
CREATE TABLE IF NOT EXISTS loan_products (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(255) UNIQUE NOT NULL,
    product_name VARCHAR(500) NOT NULL,
    provider_name VARCHAR(255) NOT NULL,
    interest_rate_min DECIMAL(5, 2),
    interest_rate_max DECIMAL(5, 2),
    min_loan_amount DECIMAL(12, 2),
    max_loan_amount DECIMAL(12, 2),
    min_tenure_months INTEGER,
    max_tenure_months INTEGER,
    -- Eligibility Criteria
    min_monthly_income DECIMAL(12, 2) DEFAULT 0,
    min_credit_score INTEGER DEFAULT 300,
    max_credit_score INTEGER DEFAULT 900,
    required_employment_status VARCHAR(255), -- comma-separated values
    min_age INTEGER DEFAULT 21,
    max_age INTEGER DEFAULT 60,
    -- Metadata
    source_url TEXT,
    source_website VARCHAR(255),
    raw_criteria JSONB, -- Store original criteria for reference
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for loan_products table
CREATE INDEX IF NOT EXISTS idx_loan_products_active ON loan_products(is_active);
CREATE INDEX IF NOT EXISTS idx_loan_products_min_income ON loan_products(min_monthly_income);
CREATE INDEX IF NOT EXISTS idx_loan_products_credit_score ON loan_products(min_credit_score, max_credit_score);
CREATE INDEX IF NOT EXISTS idx_loan_products_provider ON loan_products(provider_name);
CREATE INDEX IF NOT EXISTS idx_loan_products_last_updated ON loan_products(last_updated);

-- =====================================================
-- MATCHES TABLE
-- Stores user-loan product matches
-- =====================================================
CREATE TABLE IF NOT EXISTS matches (
    id SERIAL PRIMARY KEY,
    match_id UUID DEFAULT uuid_generate_v4() UNIQUE,
    user_id VARCHAR(255) NOT NULL REFERENCES users(user_id),
    product_id VARCHAR(255) NOT NULL REFERENCES loan_products(product_id),
    match_score DECIMAL(5, 2), -- Confidence score 0-100
    match_reason TEXT, -- Explanation of why matched
    match_type VARCHAR(50) DEFAULT 'auto', -- 'auto', 'llm_verified', 'manual'
    batch_id VARCHAR(50) NOT NULL,
    notification_sent BOOLEAN DEFAULT FALSE,
    notification_sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Prevent duplicate matches
    UNIQUE(user_id, product_id, batch_id)
);

-- Indexes for matches table
CREATE INDEX IF NOT EXISTS idx_matches_user_id ON matches(user_id);
CREATE INDEX IF NOT EXISTS idx_matches_product_id ON matches(product_id);
CREATE INDEX IF NOT EXISTS idx_matches_batch_id ON matches(batch_id);
CREATE INDEX IF NOT EXISTS idx_matches_notification_sent ON matches(notification_sent);
CREATE INDEX IF NOT EXISTS idx_matches_created_at ON matches(created_at);

-- =====================================================
-- CRAWL LOGS TABLE
-- Tracks web crawling history
-- =====================================================
CREATE TABLE IF NOT EXISTS crawl_logs (
    id SERIAL PRIMARY KEY,
    crawl_id UUID DEFAULT uuid_generate_v4() UNIQUE,
    source_website VARCHAR(255) NOT NULL,
    source_url TEXT,
    status VARCHAR(50) NOT NULL, -- 'success', 'failed', 'partial'
    products_found INTEGER DEFAULT 0,
    products_added INTEGER DEFAULT 0,
    products_updated INTEGER DEFAULT 0,
    error_message TEXT,
    duration_seconds INTEGER,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Index for crawl_logs
CREATE INDEX IF NOT EXISTS idx_crawl_logs_website ON crawl_logs(source_website);
CREATE INDEX IF NOT EXISTS idx_crawl_logs_status ON crawl_logs(status);
CREATE INDEX IF NOT EXISTS idx_crawl_logs_started_at ON crawl_logs(started_at);

-- =====================================================
-- NOTIFICATION LOGS TABLE
-- Tracks email notifications sent to users
-- =====================================================
CREATE TABLE IF NOT EXISTS notification_logs (
    id SERIAL PRIMARY KEY,
    notification_id UUID DEFAULT uuid_generate_v4() UNIQUE,
    user_id VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    subject VARCHAR(500),
    status VARCHAR(50) NOT NULL, -- 'sent', 'failed', 'bounced'
    match_ids TEXT[], -- Array of match IDs included in notification
    error_message TEXT,
    ses_message_id VARCHAR(255),
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for notification_logs
CREATE INDEX IF NOT EXISTS idx_notification_logs_user_id ON notification_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_notification_logs_status ON notification_logs(status);
CREATE INDEX IF NOT EXISTS idx_notification_logs_sent_at ON notification_logs(sent_at);

-- =====================================================
-- HELPER FUNCTIONS
-- =====================================================

-- Function to update 'updated_at' timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for users table
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- SAMPLE LOAN PRODUCTS (for testing)
-- =====================================================
INSERT INTO loan_products (
    product_id, product_name, provider_name,
    interest_rate_min, interest_rate_max,
    min_loan_amount, max_loan_amount,
    min_tenure_months, max_tenure_months,
    min_monthly_income, min_credit_score, max_credit_score,
    required_employment_status, min_age, max_age,
    source_website
) VALUES 
    ('HDFC_PL_001', 'HDFC Personal Loan', 'HDFC Bank',
     10.50, 21.00, 50000, 4000000, 12, 60,
     25000, 750, 900, 'salaried,self-employed', 21, 60,
     'hdfc.com'),
    ('ICICI_PL_001', 'ICICI Personal Loan', 'ICICI Bank',
     10.75, 19.00, 50000, 2500000, 12, 60,
     20000, 700, 900, 'salaried,self-employed', 23, 58,
     'icicibank.com'),
    ('SBI_PL_001', 'SBI Xpress Credit', 'State Bank of India',
     11.00, 14.50, 25000, 2000000, 6, 72,
     15000, 650, 900, 'salaried', 21, 58,
     'sbi.co.in'),
    ('AXIS_PL_001', 'Axis Personal Loan', 'Axis Bank',
     10.49, 22.00, 50000, 1500000, 12, 60,
     15000, 700, 900, 'salaried,self-employed', 21, 60,
     'axisbank.com'),
    ('BAJAJ_PL_001', 'Bajaj Finserv Personal Loan', 'Bajaj Finance',
     11.00, 28.00, 25000, 3500000, 12, 84,
     22000, 685, 900, 'salaried,self-employed', 21, 67,
     'bajajfinserv.in')
ON CONFLICT (product_id) DO NOTHING;

-- Grant permissions (adjust as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_user;
