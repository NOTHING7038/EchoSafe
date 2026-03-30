# EchoSafe Makefile
# Provides convenient commands for development and deployment

.PHONY: help install dev test run build deploy clean

# Default target
help:
	@echo "EchoSafe - Anonymous Reporting System"
	@echo ""
	@echo "Available commands:"
	@echo "  install    Install Python dependencies"
	@echo "  dev        Start development server with hot reload"
	@echo "  test       Run tests"
	@echo "  run        Start production server"
	@echo "  build      Build Docker image"
	@echo "  deploy     Deploy with Docker Compose"
	@echo "  clean      Clean up temporary files"
	@echo "  lint       Run code linting"
	@echo "  format     Format code with black"
	@echo "  db-reset   Reset database (development only)"
	@echo ""
	@echo "Examples:"
	@echo "  make install    # Install dependencies"
	@echo "  make dev        # Start development server"
	@echo "  make deploy     # Deploy with Docker"

# Installation
install:
	@echo "Installing Python dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Dependencies installed successfully!"

# Development
dev:
	@echo "Starting EchoSafe development server..."
	cd backend && python app.py

# Testing
test:
	@echo "Running tests..."
	cd backend && python -m pytest tests/ -v
	@echo "Tests completed!"

# Production
run:
	@echo "Starting EchoSafe production server..."
	cd backend && uvicorn app:app --host 0.0.0.0 --port 8000

# Docker build
build:
	@echo "Building Docker image..."
	docker build -t echosafe:latest .
	@echo "Docker image built successfully!"

# Docker deployment
deploy:
	@echo "Deploying EchoSafe with Docker Compose..."
	docker-compose up -d
	@echo "Deployment completed!"
	@echo "API available at: http://localhost:8000"
	@echo "MongoDB available at: localhost:27017"

# Cleanup
clean:
	@echo "Cleaning up temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	@echo "Cleanup completed!"

# Code quality
lint:
	@echo "Running code linting..."
	cd backend && flake8 app.py --max-line-length=100 --ignore=E203,W503
	@echo "Linting completed!"

format:
	@echo "Formatting code with black..."
	cd backend && black app.py --line-length 100
	@echo "Code formatted!"

# Database operations
db-reset:
	@echo "Resetting development database..."
	@echo "WARNING: This will delete all data!"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	cd backend && python -c "
from pymongo import MongoClient
client = MongoClient('mongodb://localhost:27017')
db = client['echosafe']
db.reports.delete_many({})
db.hr_users.delete_many({})
print('Database reset completed!')
"

# Health check
health:
	@echo "Checking EchoSafe API health..."
	curl -f http://localhost:8000/health || echo "API is not running"

# Logs
logs:
	docker-compose logs -f

# Stop services
stop:
	docker-compose down

# Development setup (first time)
setup: install
	@echo "Setting up development environment..."
	@echo "Creating .env file from template..."
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env file - please update with your values"; else echo ".env file already exists"; fi
	@echo "Development setup completed!"
	@echo "Next steps:"
	@echo "1. Update .env file with your configuration"
	@echo "2. Start MongoDB: mongod"
	@echo "3. Start development server: make dev"
