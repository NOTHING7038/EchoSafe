# Contributing to EchoSafe

Thank you for your interest in contributing to EchoSafe! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- MongoDB 5.0+
- Git
- Basic knowledge of FastAPI, MongoDB, and web development

### Setup Development Environment

1. **Fork the Repository**
   ```bash
   git clone https://github.com/your-username/EchoSafe.git
   cd EchoSafe
   ```

2. **Install Dependencies**
   ```bash
   make setup
   # or manually:
   pip install -r backend/requirements.txt
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your local configuration
   ```

4. **Start Development Server**
   ```bash
   make dev
   ```

## 📋 Development Workflow

### 1. Create a Branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 2. Make Changes
- Follow the existing code style and patterns
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes
```bash
make test
make lint
```

### 4. Commit Changes
```bash
git add .
git commit -m "feat: add new feature description"
```

### 5. Push and Create Pull Request
```bash
git push origin feature/your-feature-name
# Create pull request on GitHub
```

## 🏗️ Code Standards

### Python Code Style
- Follow PEP 8 guidelines
- Use Black for code formatting (100 character line length)
- Use descriptive variable and function names
- Add docstrings to all functions and classes

### Documentation
- Update README.md for user-facing changes
- Add inline comments for complex logic
- Update API documentation in docstrings

### Testing
- Write unit tests for new functionality
- Ensure all tests pass before submitting
- Aim for >80% code coverage

## 🐛 Bug Reports

When reporting bugs, please include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Relevant logs or screenshots

## ✨ Feature Requests

Feature requests should:
- Describe the problem you're trying to solve
- Explain why the feature would be valuable
- Provide implementation suggestions if possible

## 🔒 Security

If you discover a security vulnerability:
- Do not open a public issue
- Email security@echosafe.com with details
- We'll respond within 48 hours

## 📁 Project Structure

```
EchoSafe/
├── backend/                 # FastAPI backend
│   ├── app.py              # Main application
│   ├── requirements.txt    # Python dependencies
│   └── tests/              # Test files
├── frontend/               # Anonymous reporting interface
├── hr_portal/             # HR investigator dashboard
├── ai_model/              # AI/ML models
├── scripts/               # Utility scripts
├── docs/                  # Documentation
├── docker-compose.yml     # Docker configuration
├── Dockerfile            # Container build file
├── Makefile              # Development commands
└── README.md             # Project documentation
```

## 🧪 Testing

### Running Tests
```bash
# Run all tests
make test

# Run specific test file
cd backend && python -m pytest tests/test_auth.py -v

# Run with coverage
cd backend && python -m pytest --cov=app tests/
```

### Writing Tests
- Use pytest framework
- Mock external dependencies
- Test both success and failure cases
- Use descriptive test names

## 📝 Commit Message Format

We follow the Conventional Commits specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(auth): add two-factor authentication
fix(api): resolve case sensitivity in username validation
docs(readme): update installation instructions
```

## 🚀 Release Process

1. Update version number in `backend/app.py`
2. Update CHANGELOG.md
3. Create git tag: `git tag v1.0.0`
4. Push tag: `git push origin v1.0.0`
5. Create GitHub release

## 💬 Getting Help

- **Discussions**: Use GitHub Discussions for questions
- **Issues**: Report bugs or request features
- **Email**: Contact team@echosafe.com for private matters

## 📄 License

By contributing to EchoSafe, you agree that your contributions will be licensed under the same license as the project.

## 🙏 Recognition

Contributors are recognized in:
- README.md contributors section
- Release notes
- Annual contributor appreciation post

Thank you for contributing to EchoSafe and helping make workplaces safer! 🌟
