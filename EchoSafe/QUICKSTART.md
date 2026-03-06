# EchoSafe MVP - 5-Minute Quick Start

## Get Running in 5 Minutes

### 1. Install Dependencies (1 min)

```bash
cd EchoSafe/backend
pip install -r requirements.txt
```

### 2. Start Server (1 min)

```bash
python app.py
```

You'll see:
```
INFO:     Started server process [...]
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 3. Test the API (1 min)

In a new terminal:
```bash
python -c "
import requests
response = requests.post('http://localhost:8000/api/submit_report',
    json={'report_text': 'There is a threat to employee safety'})
print(response.json())
"
```

Expected output:
```
{
  'success': True,
  'case_id': '86e4723bcb2dbe68af44c57b6d40211465214b7e720da9d43e6d31c28929a5c8',
  'message': 'Report submitted successfully...'
}
```

### 4. Check Dashboard (1 min)

Register HR user and login:
```bash
# Register
curl -X POST http://localhost:8000/api/hr/register \
  -H "Content-Type: application/json" \
  -d '{"username":"investigator1","password":"SecurePass123!"}'

# Login
curl -X POST http://localhost:8000/api/hr/login \
  -H "Content-Type: application/json" \
  -d '{"username":"investigator1","password":"SecurePass123!"}'
```

You'll get a JWT token.

### 5. View Dashboard (1 min)

```bash
curl "http://localhost:8000/api/hr/dashboard?token=YOUR_TOKEN"
```

You'll see all reports sorted by urgency!

---

## What You Have

- ✓ Anonymous reporting (no accounts for reporters)
- ✓ AES-256 encryption (all data encrypted at rest)
- ✓ AI urgency scoring (keyword-based)
- ✓ HR dashboard with JWT authentication
- ✓ SQLite database (instant, no setup)
- ✓ 4 Python dependencies only

## Next Steps

1. **Customize**: Edit keywords in `backend/app.py` `score_urgency()` function
2. **Deploy**: Use Docker: `docker build -t echosafe . && docker run -p 8000:8000 echosafe`
3. **Production**: See SETUP.md for Nginx, HTTPS, SSL setup
4. **Extend**: Add email notifications, TensorFlow model, admin panel

## API Endpoints Reference

```
Reporter Endpoints:
  POST   /api/submit_report         → Submit anonymous report
  GET    /api/report/{case_id}      → View encrypted report

HR Endpoints:
  POST   /api/hr/register           → Create investigator account
  POST   /api/hr/login              → Get JWT token
  GET    /api/hr/dashboard          → View all reports
  POST   /api/hr/decrypt_report     → Decrypt specific report
  PUT    /api/hr/update_status      → Update report status
```

## Help?

- **Port already in use?** `lsof -ti:8000 | xargs kill -9`
- **Database issue?** `rm backend/echosafe.db` then restart
- **More details?** Check README.md and SETUP.md

---

**Ready to report anonymously. Decrypt privately. Investigate securely.**

## ✅ Setup Complete!

Your EchoSafe anonymous reporting system is ready to use.

## 🚀 Starting the System

### 1. Backend (FastAPI Server)
```powershell
cd c:\Users\Tirth\Downloads\THISIIT\EchoSafe\backend
"C:\Program Files\Python314\python.exe" app.py
```

The server will run at: **http://localhost:8000**

### 2. Frontend (Web Interface)
Open your browser and navigate to:
- **http://localhost:8000** - Main interface (if static files configured)
- Or open `frontend/index.html` directly in your browser

## 📋 Project Structure

```
EchoSafe/
├── backend/
│   ├── app.py              # FastAPI backend (all routes, encryption, AI logic)
│   ├── requirements.txt     # Python dependencies
│   └── echosafe.db          # SQLite database (auto-created)
├── frontend/
│   └── index.html           # Complete SPA (Reporter + HR Dashboard)
├── ai_model/
│   └── train_model.py       # AI model training script
├── Dockerfile               # Docker containerization
├── README.md                # Full documentation
└── QUICKSTART.md           # This file
```

## 🧪 Testing the System

### Test 1: Submit an Anonymous Report
1. Open **frontend/index.html** in browser
2. Go to "Submit Report" tab
3. Enter: *"There is a threat to my safety"*
4. Click "Submit Report"
5. Copy the **Case ID** (keep it safe!)
6. See the encrypted report in your database

### Test 2: Retrieve Your Report
1. Go to "Check Report" tab
2. Paste your Case ID
3. View encrypted report metadata

### Test 3: HR Dashboard
1. Go to "HR Dashboard" tab
2. Click "Register"
3. Enter username: `hr_test` | password: `test123`
4. Click "Login"
5. View all reports sorted by priority
6. Click any report to decrypt and view details
7. Update status to "investigating" or "resolved"

## 🔐 Security Features

✅ **AES-256 Encryption** - Report bodies encrypted at rest
✅ **SHA-256 Case IDs** - 100% anonymous (no personal data)
✅ **Bcrypt Passwords** - HR accounts hashed securely
✅ **JWT Tokens** - 24-hour session management
✅ **CORS Protected** - Cross-origin requests validated

## 🤖 AI Urgency Scoring

Reports are automatically scored 0.0 → 1.0:

| Score | Priority | Keywords |
|-------|----------|----------|
| 0.6-1.0 | 🔴 HIGH | threat, physical, violence, emergency, danger |
| 0.3-0.6 | 🟡 MEDIUM | harassment, discrimination, conflict |
| 0.0-0.3 | 🟢 LOW | general feedback, suggestions |

## 📦 API Endpoints

### Reporter Endpoints
- `POST /api/submit_report` - Submit anonymous report
- `GET /api/report/{case_id}` - Retrieve encrypted report

### HR Endpoints
- `POST /api/hr/register` - Create HR account
- `POST /api/hr/login` - Login (returns JWT token)
- `GET /api/hr/dashboard` - View all reports
- `POST /api/hr/decrypt_report` - View decrypted report
- `PUT /api/hr/update_status` - Update case status

## 💾 Database

The system uses **SQLite** (`echosafe.db`):
- **reports** - Encrypted reports with metadata
- **hr_users** - HR investigator accounts
- **case_tokens** - Case access management

Database is auto-created on first run.

## 🐳 Docker Deployment

```powershell
# Build image
docker build -t echosafe-mvp .

# Run container
docker run -p 8000:8000 echosafe-mvp

# Deploy to GCP Cloud Run
gcloud run deploy echosafe-mvp --source . --port 8000
```

## 🔧 Troubleshooting

### Server won't start
```
Error: ModuleNotFoundError
→ Solution: Install dependencies
```
```powershell
&"C:\Program Files\Python314\python.exe" -m pip install -r backend/requirements.txt
```

### Port 8000 already in use
```powershell
# Kill process on port 8000
Get-Process | Where-Object {$_.Name -eq "python"} | Stop-Process -Force
```

### Browser shows blank page
- Clear browser cache (Ctrl+Shift+Delete)
- Try incognito/private mode
- Check browser console (F12) for errors
- Verify backend is running: `http://localhost:8000/docs`

## 📚 Documentation

Full documentation available in:
- [README.md](README.md) - Complete feature documentation
- [.github/copilot-instructions.md](.github/copilot-instructions.md) - Development guidelines

## 🎯 Next Steps

1. ✅ Test basic report submission
2. ✅ Test HR login and dashboard
3. ⬜ Change `SECRET_KEY` in `app.py` for production
4. ⬜ Deploy with HTTPS enabled
5. ⬜ Set up automated backups
6. ⬜ Enable logging and monitoring
7. ⬜ Train custom AI model (optional)

## 📞 Support

For issues:
1. Check error logs in terminal
2. Review [README.md](README.md)
3. Verify all dependencies installed
4. Check database integrity: `sqlite3 echosafe.db ".tables"`

---

**EchoSafe MVP v1.0** | Secure Anonymous Reporting ✨
