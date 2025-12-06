#!/bin/bash
# Create loan_eligibility database if it doesn't exist

set -e

# Create loan_eligibility database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT 'CREATE DATABASE loan_eligibility' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'loan_eligibility')\gexec
    GRANT ALL PRIVILEGES ON DATABASE loan_eligibility TO $POSTGRES_USER;
EOSQL

# Connect to loan_eligibility and run schema
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "loan_eligibility" -f /docker-entrypoint-initdb.d/01_schema.sql || true
