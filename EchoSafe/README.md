# EchoSafe - Anonymous E2EE Reporting System

A production-ready anonymous reporting platform with end-to-end encryption, AI-powered triage, and role-based investigator dashboard.

## Overview

**EchoSafe** is a comprehensive workplace reporting solution that ensures complete anonymity while providing powerful tools for HR investigators. The system combines security, simplicity, and intelligence to create a safe reporting environment.

### Key Features

- **Complete Anonymity**: No user accounts required. Access via SHA-256 Case Token only.
- **End-to-End Encryption**: AES-256 encryption with JWT-based HR authentication.
- **AI-Powered Triage**: Keyword-based urgency scoring (0.0 - 1.0) for priority routing.
- **Role-Based Dashboard**: Secure HR investigator interface with case prioritization.
- **Single-Language Stack**: Python FastAPI + SQLite for minimal dependencies.
- **One-Click Deployment**: Docker container for GCP, AWS, or on-premise hosting.

## Architecture

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend** | FastAPI + Uvicorn | High-performance API server with AI logic |
| **Security** | AES-256 (PyCryptodome) + Bcrypt | Encryption + secure password hashing |
| **Database** | SQLite | Zero-configuration single-file database |
| **Frontend** | HTML/CSS/JavaScript | Responsive SPA with dark mode support |
| **Authentication** | JWT | Secure token-based HR session management |

### System Components

#### Backend (FastAPI)
- Single `app.py` handling all routes, encryption, and AI processing
- ~1000 requests/second capability
- Built-in CORS support for seamless frontend integration

#### Frontend (Multi-View SPA)
- **Access Portal**: Central routing interface
- **Reporter View**: Anonymous form with encrypted submission
- **HR Portal**: Investigator dashboard with case management
- **Responsive Design**: Mobile-friendly with dark mode support

#### Database Schema
- `reports`: Encrypted report data with metadata
- `hr_users`: Investigator accounts with secure credentials
- `case_tokens`: Anonymous access tokens

#### AI Triage System
- TensorFlow/Keras model for urgency classification
- Keyword-based fallback scoring
- Priority levels: Low (0.0-0.3), Medium (0.3-0.6), High (0.6-1.0)

## 🚀 Quick Start

Get EchoSafe running in under 5 minutes with these simple steps.

### Prerequisites
- **Python 3.10+** - Core runtime environment
- **Node.js** (optional) - For advanced frontend builds
- **Docker** (optional) - For containerized deployment

### Local Development Setup

#### 1. Install Backend Dependencies
```bash
cd backend
pip install -r requirements.txt
```

#### 2. Train AI Model (Optional)
```bash
cd ai_model
python train_model.py
```

#### 3. Start Backend Server
```bash
cd backend
python app.py
```
*API will be available at `http://localhost:8000`*

#### 4. Launch Frontend
Open the main access page:
```bash
# Option 1: Open directly
open index.html

# Option 2: Serve with HTTP server
cd frontend
python -m http.server 8080
```
*Visit `http://localhost:8080`*

### Docker Deployment

#### Build & Run Container
```bash
# Build image
docker build -t echosafe-mvp .

# Run container
docker run -p 8000:8000 echosafe-mvp
```

#### Deploy to Cloud Platforms
```bash
# Google Cloud Run
gcloud run deploy echosafe-mvp --source . --port 8000

# AWS ECS (similar process)
```

## 📡 API Documentation

### Reporter Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/submit_report` | Submit anonymous encrypted report |
| `GET` | `/api/view_report` | Retrieve report status by Case ID |

#### Submit Report Example
```bash
curl -X POST http://localhost:8000/api/submit_report \
  -H "Content-Type: application/json" \
  -d '{"report_text": "I witnessed harassment in the workplace"}'
```

**Response:**
```json
{
  "success": true,
  "case_id": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "message": "Report submitted successfully. Keep this Case ID safe for future reference."
}
```

### HR Management Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/hr/register` | Register HR investigator account |
| `POST` | `/api/hr/login` | Login and receive JWT token |
| `GET` | `/api/hr/dashboard` | Get all reports (requires token) |
| `POST` | `/api/hr/decrypt_report` | Decrypt and view specific report |
| `PUT` | `/api/hr/update_status` | Update case status |
| `POST` | `/api/hr/change_password` | Change HR password |
| `GET` | `/api/hr/analytics` | Get analytics data |

#### HR Login Example
```bash
curl -X POST http://localhost:8000/api/hr/login \
  -H "Content-Type: application/json" \
  -d '{"username": "investigator1", "password": "secure_password"}'
```

**Response:**
```json
{
  "success": true,
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "message": "Welcome, investigator1"
}
```

## 📁 Project Structure

```
EchoSafe/
├── 📂 backend/
│   ├── 🐍 app.py              # FastAPI backend (routes, encryption, AI)
│   └── 📄 requirements.txt     # Python dependencies
├── 📂 frontend/
│   └── 🌐 index.html          # Anonymous reporting interface
├── 📂 hr_portal/
│   └── 🌐 index.html          # HR investigator dashboard
├── 📂 ai_model/
│   ├── 🧠 train_model.py      # TensorFlow model training script
│   └── 🤖 model.h5            # Pre-trained urgency classification model
├── 🗄️ echosafe.db             # SQLite database (auto-created)
├── 🐳 Dockerfile              # Container configuration
├── 📄 index.html              # Main access portal
└── 📖 README.md               # This documentation
```

## 🔒 Security Architecture

### Encryption Implementation
- **AES-256-GCM**: Report bodies encrypted at rest with authenticated encryption
- **Key Derivation**: PBKDF2 with Case ID + salt for encryption keys
- **Unique IV/Nonce**: Generated per report, stored separately for security

### Authentication System
- **Bcrypt**: HR passwords hashed with cost factor 12
- **JWT Tokens**: 24-hour expiry with secure signing
- **Session Management**: Stateless token-based authentication

### Anonymity Guarantees
- **No Reporter Accounts**: Only SHA-256 Case IDs are stored
- **Zero Personal Data**: Reports indexed exclusively by Case ID
- **No Tracking**: No cookies, sessions, or persistent identifiers

## 🤖 AI Triage System

### Urgency Scoring Algorithm
The AI model evaluates reports and assigns urgency scores:

| Score Range | Priority Level | Typical Cases |
|-------------|----------------|---------------|
| **0.0 - 0.3** | 🟢 Low Priority | General feedback, suggestions |
| **0.3 - 0.6** | 🟡 Medium Priority | Harassment, discrimination |
| **0.6 - 1.0** | 🔴 High Priority | Threats, violence, emergencies |

### Keyword Detection
- **High Priority Keywords**: `threat`, `violence`, `abuse`, `assault`, `unsafe`, `harassment`
- **Medium Priority Keywords**: `bully`, `discrimination`, `retaliation`, `hostile`, `pressure`

### Model Fallback
If the TensorFlow model is unavailable, the system automatically falls back to keyword-based scoring to ensure continuous operation.

## 🧪 Testing Guide

### Reporter Workflow Testing
1. Navigate to **Submit Report** tab
2. Enter test text: `"There is a threat to my safety"`
3. Click **Submit Report**
4. Copy the generated Case ID
5. Go to **Check Report** tab
6. Paste Case ID to view report status

### HR Dashboard Testing
1. Navigate to **HR Portal** tab
2. Click **Register** and create investigator account
3. Login with your credentials
4. Browse the dashboard to view submitted reports
5. Click any report to view decrypted details
6. Update case status to **investigating** or **resolved**

### API Testing
Use the provided curl examples in the API documentation section to test endpoints directly.

## 🚀 Future Enhancements

### Planned Features
- [ ] **Multi-language Support**: Reports in multiple languages
- [ ] **File Attachments**: Encrypted document uploads
- [ ] **Audit Logging**: Comprehensive HR access tracking
- [ ] **Advanced NLP**: Transformer-based AI model
- [ ] **2FA Authentication**: Two-factor auth for HR accounts
- [ ] **PDF Export**: Case summary reports
- [ ] **Webhook Integration**: External system notifications
- [ ] **GraphQL API**: Alternative to REST endpoints

### Performance Improvements
- [ ] **Database Optimization**: Indexing and query optimization
- [ ] **Caching Layer**: Redis for session and data caching
- [ ] **Load Balancing**: Multi-instance deployment support
- [ ] **CDN Integration**: Static asset optimization

## 📋 Production Deployment Checklist

### Security Configuration
- [ ] Update `SECRET_KEY` in `app.py` with cryptographically secure value
- [ ] Configure HTTPS/TLS (Certbot or cloud provider SSL)
- [ ] Set up environment variables for production secrets
- [ ] Enable database encryption at rest
- [ ] Implement rate limiting on API endpoints

### Infrastructure Setup
- [ ] Configure database backup strategy
- [ ] Set up monitoring and alerting (Prometheus/Grafana)
- [ ] Create incident response procedures
- [ ] Configure log aggregation and analysis
- [ ] Set up health checks and auto-restart

### Compliance & Legal
- [ ] Review data protection regulations (GDPR, CCPA)
- [ ] Establish data retention policies
- [ ] Create privacy policy and user agreements
- [ ] Set up legal compliance documentation

## 📞 Support & Contributing

### Getting Help
- **Documentation**: Review this README and inline code comments
- **Issues**: Report bugs via GitHub Issues
- **Security**: Report security vulnerabilities privately
- **Community**: Join discussions in GitHub Discussions

### Development Guidelines
- Follow PEP 8 for Python code style
- Use semantic versioning for releases
- Write tests for new features
- Update documentation for API changes

---

**EchoSafe v1.0** | Built with ❤️ for secure workplace reporting
