# EchoSafe MVP - Anonymous E2EE Reporting System

**EchoSafe** is a lean, production-ready anonymous reporting platform with end-to-end encryption, AI-powered triage, and role-based investigator dashboard.

## Core Features ✓

- **100% Anonymous**: No user accounts needed for reporters. Access via SHA-256 Case Token only.
- **E2E Encryption (AES-256)**: Reports encrypted at submission, only HR can decrypt with case ID.
- **AI Triage**: Keyword-based urgency scoring (0.0 - 1.0) for priority routing.
- **HR Dashboard**: JWT-authenticated investigators view all reports sorted by urgency.
- **Single-Language Stack**: Python FastAPI + SQLite (minimal dependencies).
- **One-Click Deployment**: Docker container for GCP, AWS, or on-premise hosting.

## Tech Stack

| Component | Tech | Purpose |
|-----------|------|---------|
| **Backend** | FastAPI + Uvicorn | API server + AI logic |
| **Security** | AES-256 (PyCryptodome) + Bcrypt | Encryption + password hashing |
| **Database** | SQLite | Single .db file (no setup) |
| **Frontend** | HTML/JS | Anonymous form + HR dashboard |
| **Authentication** | JWT | HR session tokens |

## Quick Start (< 5 minutes)

EchoSafe is a minimal viable product (MVP) designed to enable anonymous, secure reporting with AI-powered triage. The system ensures complete anonymity through SHA-256 Case IDs (no user accounts for reporters) and protects report content via AES-256 encryption.

### Core Features

- 🔐 **Complete Anonymity**: No personal data stored; reporters identified only by Case ID
- 🔒 **End-to-End Encryption**: AES-256 encryption at rest; JWT for HR authentication
- 🤖 **AI Triage**: TensorFlow/Keras model scores report urgency (0.0 to 1.0)
- 📊 **Role-Based Dashboard**: HR investigators view prioritized reports
- 🚀 **Docker Ready**: One-click deployment to GCP or any cloud provider

---

## Architecture

### Backend (FastAPI)
- Single `app.py` file handles all routes, encryption, and AI logic
- Fast API serving ~1000 req/sec
- Built-in CORS support for React frontend

### Frontend (React/Vanilla JS)
- Two-view SPA:
  - **Reporter View**: Anonymous form to submit encrypted reports
  - **HR View**: Investigator login + dashboard with case prioritization
- Modal-based report detail view with decryption

### Database (SQLite)
- Single `.db` file for MVP simplicity
- Three tables: `reports`, `hr_users`, `case_tokens`

### AI Model (TensorFlow/Keras)
- Simple NLP model for urgency classification
- Keyword-based fallback if model unavailable
- Scores: 0.0 (low priority) → 1.0 (high priority)

---

## Setup Instructions

### Prerequisites
- Python 3.10+
- Node.js (optional, for advanced frontend builds)
- Docker (optional, for containerized deployment)

### Local Development

#### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

#### 2. Train AI Model (Optional)
```bash
cd ai_model
python train_model.py
```

#### 3. Run Backend Server
```bash
cd backend
python app.py
```

The API will be available at `http://localhost:8000`

#### 4. Open Frontend
Open `frontend/index.html` in a browser or serve it with a simple HTTP server:
```bash
cd frontend
python -m http.server 8080
```

Visit `http://localhost:8080`

### Docker Deployment

#### 1. Build Image
```bash
docker build -t echosafe-mvp .
```

#### 2. Run Container
```bash
docker run -p 8000:8000 echosafe-mvp
```

#### 3. Deploy to GCP
```bash
gcloud run deploy echosafe-mvp --source . --port 8000
```

---

## API Endpoints

### Reporter Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/submit_report` | Submit anonymous encrypted report |
| GET | `/api/report/{case_id}` | Retrieve encrypted report by Case ID |

#### Example: Submit Report
```bash
curl -X POST http://localhost:8000/api/submit_report \
  -H "Content-Type: application/json" \
  -d '{"report_text": "I witnessed harassment in the workplace"}'
```

Response:
```json
{
  "success": true,
  "case_id": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "message": "Report submitted successfully. Keep this Case ID safe for future reference."
}
```

### HR Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/hr/register` | Register HR investigator account |
| POST | `/api/hr/login` | Login and receive JWT token |
| GET | `/api/hr/dashboard` | Get all reports (requires token) |
| POST | `/api/hr/decrypt_report` | Decrypt and view specific report |
| PUT | `/api/hr/update_status` | Update case status (pending/investigating/resolved) |

#### Example: HR Login
```bash
curl -X POST http://localhost:8000/api/hr/login \
  -H "Content-Type: application/json" \
  -d '{"username": "investigator1", "password": "secure_password"}'
```

Response:
```json
{
  "success": true,
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "message": "Welcome, investigator1"
}
```

---

## File Structure

```
EchoSafe/
├── backend/
│   ├── app.py              # FastAPI backend (routes, encryption, AI)
│   └── requirements.txt     # Python dependencies
├── frontend/
│   └── index.html          # React SPA (two-view reporting + HR dashboard)
├── ai_model/
│   ├── train_model.py      # TensorFlow model training script
│   └── model.h5            # Pre-trained urgency classification model
├── echosafe.db             # SQLite database (auto-created)
├── Dockerfile              # Container configuration
└── README.md               # This file
```

---

## Security Considerations

### Encryption
- **AES-256-GCM**: Report bodies encrypted at rest
- **Derivation**: Encryption key derived from Case ID + salt using PBKDF2
- **IV/Nonce**: Unique for each report, stored separately

### Authentication
- **Bcrypt**: HR passwords hashed with bcrypt (cost=12)
- **JWT**: Token-based auth for HR dashboard (24-hour expiry)

### Anonymity
- **No Accounts for Reporters**: Only Case ID (SHA-256) stored
- **No Personal Data**: Reports indexed only by Case ID
- **No Tracking**: No cookies, sessions, or identifiers for reporters

---

## AI Urgency Scoring

The model scores reports on severity:

**0.0 - 0.3**: Low Priority (general feedback, suggestions)
**0.3 - 0.6**: Medium Priority (harassment, discrimination)
**0.6 - 1.0**: High Priority (threats, violence, emergencies)

### Keywords Detected
- **High Priority**: threat, physical, violence, emergency, immediate, danger
- **Medium Priority**: harassment, discrimination, conflict, inappropriate

If a pre-trained model is unavailable, the system falls back to keyword-based scoring.

---

## Testing

### Test Report Submission
1. Go to "Submit Report" tab
2. Enter sample text: "There is a threat to my safety"
3. Click "Submit Report"
4. Copy the Case ID
5. Go to "Check Report" tab
6. Paste Case ID to view encrypted data

### Test HR Dashboard
1. Go to "HR Dashboard" tab
2. Click "Register" and create account
3. Login with credentials
4. Click on any report to view decrypted details
5. Update status to "investigating" or "resolved"

---

## Future Enhancements

- [ ] Multi-language support for reports
- [ ] Document/file attachment support (encrypted)
- [ ] Audit logging for HR access
- [ ] Advanced NLP model with transformer architecture
- [ ] Two-factor authentication for HR accounts
- [ ] PDF export with case summaries
- [ ] Webhook integrations for external systems
- [ ] GraphQL API alternative to REST

---

## Deployment Checklist

- [ ] Change `SECRET_KEY` in `app.py` to a strong random value
- [ ] Set up HTTPS/TLS (use Certbot or cloud provider SSL)
- [ ] Configure environment variables for production
- [ ] Set up database backups
- [ ] Enable database encryption at rest
- [ ] Implement rate limiting on API endpoints
- [ ] Set up monitoring and alerting
- [ ] Create incident response procedures

---

## Support

For issues or questions, please contact the development team or file an issue in the project repository.

---

**EchoSafe MVP v1.0** | Built with ❤️ for secure reporting
