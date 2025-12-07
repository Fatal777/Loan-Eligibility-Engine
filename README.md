# 🏦 Loan Eligibility Engine

An automated system that ingests user data, discovers personal loan products from public websites, matches users to eligible products, and notifies them via email

> 📖 **For comprehensive documentation**, see [README_DETAILED.md]

## 🚀 Live AWS Deployment

This project is fully deployed on AWS. Here are the live endpoints:

| Resource | URL/Endpoint |
|----------|--------------|
| **API Gateway** | `https://c41a2ucawd.execute-api.ap-south-1.amazonaws.com/dev` |
| **Health Check** | `GET /health` |
| **Get Upload URL** | `GET /upload/presigned-url` |
| **Trigger Matching** | `POST /trigger/matching` |
| **S3 Bucket** | `loan-eligibility-csv-uploads-202533497839` |
| **RDS PostgreSQL** | `loan-eligibility-db.chyeiw00stv1.ap-south-1.rds.amazonaws.com` |
| **n8n Dashboard** | `http://localhost:5678` (self-hosted) |
| **AWS Region** | `ap-south-1` (Mumbai) |

### Current Database Stats

| Metric | Value |
|--------|-------|
| Users Loaded | 10,000 |
| Loan Products | 8 (from 10 banks) |
| Matches Created | 25,610 |
| Batch ID | `20251206173422` |

### Quick Test Commands

```bash
# Health Check
curl https://c41a2ucawd.execute-api.ap-south-1.amazonaws.com/dev/health

# Get Presigned URL for Upload
curl "https://c41a2ucawd.execute-api.ap-south-1.amazonaws.com/dev/upload/presigned-url?filename=test.csv"

# Trigger Matching (POST)
curl -X POST https://c41a2ucawd.execute-api.ap-south-1.amazonaws.com/dev/trigger/matching \
  -H "Content-Type: application/json" \
  -d '{"batchId": "20251206173422"}'
```

---

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup & Deployment](#setup--deployment)
- [n8n Workflow Configuration](#n8n-workflow-configuration)
- [Design Decisions](#design-decisions)
- [API Reference](#api-reference)
- [Testing](#testing)

---

## 🔐 Event-Driven Upload Pattern

We counter Lambda timeout and request size limits using a **professional event-driven pattern**:

1. **Presigned URL Generation** - Frontend requests a presigned URL from Lambda (lightweight, <1s)
2. **Direct S3 Upload** - Frontend uploads CSV directly to S3 (bypasses Lambda, no size limits)
3. **S3 Event Trigger** - S3 triggers processCSV Lambda automatically on file upload
4. **Async Processing** - Lambda processes CSV in background (no timeout constraints)

This pattern:
- ✅ Eliminates Lambda 30-second timeout issues
- ✅ Removes request payload size limits (10 MB)
- ✅ Provides immediate user feedback
- ✅ Scales to multi-GB files
- ✅ Follows AWS best practices

See `src/handlers/upload.py` for implementation.

---

## 🏗️ Architecture Overview

![Architecture Diagram](./Diagram.png)

### Data Flow

1. **CSV Upload**: User uploads CSV via frontend → Presigned URL → Direct S3 upload
2. **Processing**: S3 event triggers Lambda → Parse CSV → Store in PostgreSQL → Trigger n8n webhook
3. **Crawling** (Daily): n8n crawls financial websites → Extracts loan products → Stores in database
4. **Matching**: n8n fetches users & products → Multi-stage filtering → Stores matches
5. **Notification**: n8n generates personalized emails → Sends via AWS SES

---

## ✨ Features

- **Scalable CSV Upload**: Event-driven S3 upload pattern avoiding Lambda limits
- **Automated Web Crawling**: Daily discovery of loan products from financial websites
- **Intelligent Matching**: Multi-stage optimization pipeline for efficient user-loan matching
- **Email Notifications**: Personalized HTML emails via AWS SES
- **Self-Hosted Workflow Engine**: n8n for visual workflow automation

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.11, AWS Lambda |
| Database | Amazon RDS PostgreSQL |
| Storage | Amazon S3 |
| Email | Amazon SES |
| Workflow | n8n (self-hosted via Docker) |
| Infrastructure | Serverless Framework |
| Frontend | HTML, CSS, JavaScript (Vanilla) |
| AI (Optional) | Google Gemini / OpenAI GPT |

---

## 📁 Project Structure

```
loan-eligibility-engine/
├── serverless.yml              # AWS infrastructure definition
├── docker-compose.yml          # n8n Docker setup
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
│
├── src/
│   ├── __init__.py
│   └── handlers/
│       ├── __init__.py
│       ├── upload.py           # Presigned URL generation
│       ├── process_csv.py      # CSV processing & storage
│       ├── trigger_matching.py # Manual workflow trigger
│       └── health.py           # Health check endpoint
│
├── database/
│   └── init/
│       └── 01_schema.sql       # Database schema & sample data
│
├── n8n/
│   └── workflows/
│       ├── workflow_a_crawler.json      # Loan product discovery
│       ├── workflow_b_matching.json     # User-loan matching
│       └── workflow_c_notification.json # Email notifications
│
├── frontend/
│   ├── index.html              # Upload UI
│   ├── styles.css              # Styling
│   └── app.js                  # Frontend logic
│
└── docs/
    └── architecture.md         # Detailed architecture docs
```

---

## 📦 Prerequisites

1. **AWS Account** with Free Tier access
2. **AWS CLI** configured with credentials
3. **Node.js** v18+ and npm
4. **Docker** and Docker Compose
5. **Python** 3.11+
6. **Serverless Framework** (`npm install -g serverless`)

---

## 🚀 Setup & Deployment

### Step 1: Clone Repository

```bash
git clone https://github.com/Fatal777/Loan-Eligibility-Engine.git
cd Loan-Eligibility-Engine
```

### Step 2: Set Up Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# On Windows (Command Prompt):
venv\Scripts\activate.bat

# On macOS/Linux:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### Step 3: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your values
# - AWS credentials
# - RDS database credentials
# - n8n configuration
# - AI API keys (optional)
```

### Step 4: Set Up Amazon RDS PostgreSQL

1. Create RDS PostgreSQL instance via AWS Console
2. Configure security group to allow n8n and Lambda access
3. Note the endpoint, username, and password
4. Connect and run the schema:

```bash
psql -h your-rds-endpoint -U your-username -d loan_eligibility -f database/init/01_schema.sql
```

### Step 5: Deploy AWS Infrastructure

```bash
# Install Serverless plugins
npm install

# Deploy to AWS
serverless deploy --stage dev

# Note the API Gateway URL from output
```

### Step 6: Launch n8n

```bash
# Start n8n with Docker Compose
docker-compose up -d

# Access n8n at http://localhost:5678
# Default credentials: admin / admin123 (change in .env)
```

### Step 7: Configure n8n

1. **Add PostgreSQL Credentials**:
   - Go to Settings → Credentials → Add Credential
   - Select "Postgres"
   - Enter your RDS connection details
   - Name it "Loan Eligibility DB"

2. **Add AWS Credentials**:
   - Add credential for "AWS"
   - Enter Access Key ID and Secret Key
   - Select region (us-east-1)

3. **Import Workflows**:
   - Go to Workflows → Import from File
   - Import all three workflow JSON files from `n8n/workflows/`

4. **Activate Workflows**:
   - Open each workflow
   - Click "Active" toggle
   - Save

### Step 8: Configure Frontend

```javascript
// Edit frontend/app.js
const CONFIG = {
    API_BASE_URL: 'https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/dev'
};
```

### Step 9: Verify AWS SES

```bash
# Verify sender email (required in sandbox mode)
aws ses verify-email-identity --email-address noreply@yourdomain.com

# For testing, also verify recipient emails
aws ses verify-email-identity --email-address test@example.com
```

---

## ⚙️ n8n Workflow Configuration

### Workflow A: Loan Product Discovery (Web Crawler)

| Setting | Value |
|---------|-------|
| Trigger | Schedule (Daily at 00:00 UTC) + Manual |
| Websites | BankBazaar, PaisaBazaar, MyLoanCare |
| Output | loan_products table |

**Features**:
- Real web crawling from loan aggregator sites
- Extracts: product name, provider, interest rates, loan amounts, eligibility criteria
- Robust error handling (continues if one site fails)
- Deduplication with UPSERT

### Workflow B: User-Loan Matching (Scalable)

| Setting | Value |
|---------|-------|
| Trigger | Webhook (POST /webhook/trigger-matching) + Manual |
| Batch Size | 500 users per iteration |
| Output | matches table |

**Scalability Features**:
- Self-looping: automatically processes next batch until done
- SQL-based matching (not n8n loops) for performance
- Race-safe with `FOR UPDATE SKIP LOCKED`
- Auto-triggers Workflow C when complete

### Workflow C: User Notification (Production Scale)

| Setting | Value |
|---------|-------|
| Trigger | Webhook (POST /webhook/trigger-notification) + Manual |
| Email Service | AWS SES (ap-south-1) |
| Batch Size | 1000 users per iteration |
| Template | Personalized HTML with loan details |

**Features**:
- Bulk fetch with SQL aggregation (products grouped per user)
- Beautiful HTML email template with match scores
- Self-looping for unlimited scale
- Tracks notification status in database

---

## 💡 Design Decisions

### 1. Event-Driven CSV Upload

**Problem**: Direct Lambda upload hits size limits (6MB payload) and timeout issues.

**Solution**: Presigned URL pattern
- Frontend requests presigned URL from Lambda
- Frontend uploads directly to S3
- S3 event triggers processing Lambda

**Benefits**:
- Supports files up to 5GB
- No Lambda timeout issues
- Reduced costs (no Lambda for upload)

### 2. Optimization Treasure Hunt Solution

**Problem**: Matching thousands of users against dozens of products is O(n×m) complexity. Using LLM for every pair is slow and expensive.

**Solution**: Multi-Stage Filtering Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                  OPTIMIZATION PIPELINE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Stage 1: SQL Pre-Filter                                         │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ • Only fetch active products                             │    │
│  │ • Only fetch unprocessed users from current batch        │    │
│  │ • Reduces dataset before n8n processing                  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           ↓                                      │
│  Stage 2: Index-Based Bucketing                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ • Group products by credit score ranges:                 │    │
│  │   [300-500] [500-650] [650-750] [750-900]               │    │
│  │ • User only compared against relevant bucket             │    │
│  │ • Reduces comparisons by ~75%                            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           ↓                                      │
│  Stage 3: Rule-Based Matching                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ • Fast boolean eligibility checks:                       │    │
│  │   ✓ Credit score in range                                │    │
│  │   ✓ Monthly income ≥ minimum                             │    │
│  │   ✓ Age in range                                         │    │
│  │   ✓ Employment status matches                            │    │
│  │ • Calculate confidence score (0-100)                     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           ↓                                      │
│  Stage 4: LLM Verification (Optional)                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ • Only for matches with score 50-70 (edge cases)         │    │
│  │ • Typically <10% of matches need LLM review              │    │
│  │ • Evaluates qualitative factors                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

**Results**:
- 10,000 users × 50 products = 500,000 comparisons (naive)
- With bucketing: ~125,000 comparisons
- LLM calls: ~12,500 (only edge cases)
- **Cost reduction: 75%+ in compute, 97.5% in LLM calls**

### 3. Web Crawling Strategy

**Approach**:
- Target loan aggregator sites (BankBazaar, PaisaBazaar) for broad coverage
- Also crawl individual bank sites for accuracy
- Use regex patterns for basic extraction
- Optional AI-powered extraction for complex layouts

**Robustness**:
- Continue on failure (one site down doesn't stop workflow)
- Store raw criteria for audit trail
- Last updated timestamp for freshness tracking

---

## 📡 API Reference

### Local Development Setup (Docker)

For local testing without AWS:

```bash
# Start PostgreSQL + n8n containers
docker-compose up -d

# Start local Flask API
python local_api.py

# Access points:
# - Local API: http://localhost:3000
# - n8n: http://localhost:5678
# - PostgreSQL: localhost:5432
```

**Verified Email Configuration (AWS SES)**:
- Sender: `saadilkal.10@gmail.com`
- Region: `ap-south-1` (Mumbai)

### GET /upload/presigned-url

Get a presigned URL for S3 upload.

**Query Parameters**:
- `filename` (optional): Original filename for metadata

**Response**:
```json
{
  "success": true,
  "presignedUrl": "https://bucket.s3.amazonaws.com/...",
  "uploadId": "uuid",
  "key": "uploads/timestamp_uuid.csv",
  "expiresIn": 3600
}
```

### POST /trigger/matching

Manually trigger matching workflow.

**Body**:
```json
{
  "batchId": "20241205120000"  // optional, defaults to latest
}
```

### GET /health

Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "service": "loan-eligibility-engine",
  "version": "1.0.0"
}
```

---

## 🧪 Testing

### Test CSV Upload

1. Open `frontend/index.html` in browser
2. Upload the sample `users.csv` file
3. Check S3 bucket for uploaded file
4. Check RDS for stored users
5. Verify n8n workflow execution

### Test Matching Workflow

```bash
# Trigger manually via API
curl -X POST https://your-api/dev/trigger/matching \
  -H "Content-Type: application/json" \
  -d '{"batchId": "your-batch-id"}'
```

### Test Email Notification

1. Ensure SES is configured
2. Add test email to verified identities
3. Run matching workflow
4. Check inbox for notification

---

## 📄 License

MIT License - See LICENSE file for details.

---

## 👥 Contributors

- [Saad Ilkal](https://github.com/Fatal777)

---

## 📧 Contact

For questions or issues, please open a GitHub issue or contact:
- saadilkal.10@gmail.com
